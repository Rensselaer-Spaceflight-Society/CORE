"""
The solver: works out what order to run the modules in, and handles the loops.

Three things happen here.

  1. BUILD THE GRAPH. Every module declared what it reads and writes, so the
     edges come for free: if module A writes 'D2_m' and module B reads it,
     then A runs before B. Nobody hand-maintains an execution order.

  2. TOPOLOGICALLY SORT IT. Most of a gas turbine design point is a straight
     line: requirements -> cycle -> sizing -> components. That part just runs
     in order, once.

  3. HANDLE THE GENUINE LOOPS. A few things really are circular. The combustor
     reference area depends on its own pressure loss; the casing outer diameter
     and the combustor liner diameter constrain each other; the shaft, bearings
     and rotordynamics all need each other's answers. Where the graph has a
     cycle, the solver groups those modules into a block and iterates them to
     a fixed point instead of giving up.

  4. THE OUTER REFINEMENT LOOP. The design point is computed with ASSUMED
     component efficiencies. Once geometry exists, some modules can predict
     what efficiency that geometry would actually achieve. Feeding that back
     and re-running is the outer loop. It is run explicitly by run.py, not
     hidden in here.
"""

from __future__ import annotations
from collections import defaultdict
import math


class SolverError(Exception):
    pass


class Plan:
    """An ordered list of execution blocks. A block is either one module or a
    group that has to be iterated together."""

    def __init__(self, blocks, producers):
        self.blocks = blocks
        self.producers = producers

    @property
    def is_pure_dag(self):
        return all(len(b) == 1 and not set(b[0].reads)&set(b[0].writes) for b in self.blocks)

    def describe(self):
        lines = []
        n = 0
        for block in self.blocks:
            if len(block) == 1 and not set(block[0].reads)&set(block[0].writes):
                n += 1
                lines.append(f"{n:>3}. {block[0].name}")
            else:
                names = ", ".join(m.name for m in block)
                n += 1
                lines.append(f"{n:>3}. [iterate to convergence: {names}]")
        return "\n".join(lines)


def build_plan(specs, seeded):
    """Order the modules. `seeded` is the set of variable names that already
    exist before any module runs (the seed set and the limits)."""
    specs = list(specs)
    producers = {}

    for m in specs:
        for w in m.writes:
            if w in producers:
                raise SolverError(
                    f"'{w}' is written by both {producers[w].name} and {m.name}. "
                    f"Exactly one module owns each variable -- that is what makes it "
                    f"possible to answer 'where did this number come from?'. "
                    f"Decide which module owns it and have the other one read it."
                )
            if w in seeded:
                raise SolverError(
                    f"{m.name} writes '{w}', but '{w}' is also a seed value in "
                    f"config/seed.yaml. A variable is either chosen by a human or "
                    f"computed by a module, never both."
                )
            producers[w] = m

    # unmet reads
    for m in specs:
        for r in m.reads:
            if r not in producers and r not in seeded:
                raise SolverError(
                    f"{m.name} reads '{r}' but nothing produces it and it is not a seed. "
                    f"Either add it to config/seed.yaml (if a human picks it) or write "
                    f"the module that computes it."
                )

    # edges: producer -> consumer
    deps = {m.name: set() for m in specs}
    for m in specs:
        for r in m.reads:
            p = producers.get(r)
            if p is not None:
                deps[m.name].add(p.name)

    by_name = {m.name: m for m in specs}
    order = _tarjan_scc(deps)

    blocks = []
    for group in order:
        blocks.append([by_name[n] for n in group])

    return Plan(blocks, producers)


def _tarjan_scc(deps):
    """Strongly connected components in dependency order.

    Returns a list of groups; each group is a list of module names. Groups come
    out in an order where every group's dependencies appear before it. A group
    of size 1 is an ordinary sequential step; a larger group is a genuine
    circular dependency that has to be iterated.
    """
    index = {}
    low = {}
    on_stack = defaultdict(bool)
    stack = []
    result = []
    counter = [0]

    def strongconnect(v):
        # iterative to avoid blowing the recursion limit on a big graph
        work = [(v, iter(sorted(deps[v])))]
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        while work:
            node, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter[0]
                    counter[0] += 1
                    stack.append(w)
                    on_stack[w] = True
                    work.append((w, iter(sorted(deps[w]))))
                    advanced = True
                    break
                elif on_stack[w]:
                    low[node] = min(low[node], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == node:
                        break
                result.append(comp)

    for v in sorted(deps):
        if v not in index:
            strongconnect(v)

    return result


def run_plan(plan, state, guesses=None, max_block_iters=300, tol=1e-8,
             relax=0.35, trace=False):
    """Execute a plan against a state dict. Mutates and returns the state."""
    if not math.isfinite(relax) or not 0 < relax <= 1 or not math.isfinite(tol) or tol <= 0:
        raise SolverError("relax must be in (0,1] and tol finite/positive")
    if not isinstance(max_block_iters,int) or max_block_iters < 1:
        raise SolverError("max_block_iters must be a positive integer")
    guesses = guesses or {}
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in {**state,**guesses}.values()):
        raise SolverError("state and guesses must contain finite numbers")
    log = []
    for block in plan.blocks:
        if len(block) == 1 and not set(block[0].reads)&set(block[0].writes):
            m = block[0]
            out = m.run(state)
            state.update(out)
            if trace:
                log.append(f"  ran {m.name}")
        else:
            ordered, tear_vars = _order_block(block, state)
            names = [m.name for m in ordered]

            # Only the TEAR VARIABLES need a first guess -- the ones that get
            # read inside the loop before anything in the loop has written them.
            # Everything else the block produces falls out on the first pass.
            for w in sorted(tear_vars):
                if w in state:
                    continue
                if w not in guesses:
                    raise SolverError(
                        f"'{w}' is the tear variable for the coupled group {names} "
                        f"and has no first guess. Add it to config/initial_guess.yaml "
                        f"-- an iteration has to start somewhere. It does not have to "
                        f"be right, only roughly the correct size."
                    )
                state[w] = guesses[w]

            converged = False
            delta = float("inf")
            for i in range(max_block_iters):
                before = {w: state[w] for m in ordered for w in m.writes if w in state}
                for m in ordered:
                    out = m.run(state)
                    # UNDER-RELAXATION. A plain fixed-point iteration on a
                    # strongly coupled block oscillates: the combustor liner
                    # grows, the casing grows to contain it, the combustor sees
                    # more room and grows again. Blending each pass toward the
                    # new value instead of jumping to it damps that out. The
                    # converged answer is identical -- relaxation only changes
                    # the path, never the fixed point.
                    for k, v in out.items():
                        if k in state and isinstance(v, (int, float)) and not isinstance(v, bool):
                            state[k] = (v if k.endswith('_count') or isinstance(v,int)
                                        else state[k] + relax * (v-state[k]))
                        else:
                            state[k] = v
                after = {w: state[w] for m in ordered for w in m.writes}
                # Test the unrelaxed fixed-point residual at the candidate state.
                # Tiny relaxation cannot make an unconverged solution appear converged.
                delta = max(_rel_delta({k: state[k] for k in m.writes}, m.run(state)) for m in ordered)
                if trace:
                    log.append(f"  loop [{', '.join(names)}] pass {i+1}: delta={delta:.3e}")
                if delta < tol and i > 0:
                    converged = True
                    break
            if not converged:
                raise SolverError(
                    f"the coupled group {names} did not converge in {max_block_iters} passes "
                    f"(last relative change {delta:.3e}, relaxation {relax}).\n"
                    f"  Try a smaller relaxation factor, a better first guess in "
                    f"config/initial_guess.yaml, or breaking the loop by promoting one of "
                    f"its variables to a seed value.\n"
                    f"  A block that will not converge at any relaxation usually means two "
                    f"modules disagree about a quantity rather than merely lagging on it."
                )
    return state, log


def _order_block(block, state):
    """Order the modules inside a coupled block, and find the tear variables.

    A coupled block has no valid topological order by definition -- that is what
    makes it coupled. But most of it usually IS orderable; only one or two edges
    actually close the loop. Those edges' variables are the tear variables, and
    they are the only ones that need a first guess.

    Greedy: repeatedly take whichever remaining module has the fewest of its
    in-block inputs still unsatisfied. Anything still unsatisfied when a module
    is scheduled becomes a tear variable.
    """
    in_block_writers = {}
    for m in block:
        for w in m.writes:
            in_block_writers[w] = m.name

    remaining = list(block)
    available = set(state) | {v for v in in_block_writers if v in state}
    ordered = []
    tear = set()

    while remaining:
        def unmet(m):
            return [r for r in m.reads if r in in_block_writers and r not in available]

        remaining.sort(key=lambda m: (len(unmet(m)), m.name))
        pick = remaining.pop(0)
        for r in unmet(pick):
            tear.add(r)
            available.add(r)
        ordered.append(pick)
        available.update(pick.writes)

    return ordered, tear


def _rel_delta(a, b):
    worst = 0.0
    for k in a:
        old, new = a[k], b[k]
        if isinstance(old, bool) or isinstance(new, bool):
            worst = max(worst, 0.0 if old == new else 1.0)
            continue
        scale = max(abs(old), abs(new), 1e-12)
        worst = max(worst, abs(new - old) / scale)
    return worst
