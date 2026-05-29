# Submission Notes — Google Form

> Copy-paste the sections below directly into the Google Form fields.
> Form link: https://forms.gle/51xrFoUeGj9PD6KQA

---

## Field: "The approach / framework you used for scheduling"

I used a **simulation-based greedy look-ahead** approach.

Buses are sorted by departure time and scheduled one at a time. For each bus, I generate every physically valid combination of charging stations — filtered by two hard constraints: the 240 km range limit between any two consecutive stops, and strict route-order (no backtracking). That gives at most 8–16 candidate plans per bus.

I then simulate each candidate plan against the **current committed queue state** of all stations — accounting for any buses already scheduled ahead of it — and score each simulation using three weighted soft metrics: individual wait time, operator fleet consistency, and overall trip duration. The plan with the lowest composite score wins and gets committed. That committed state is what the next bus sees when it's its turn.

This means earlier-departing buses naturally get priority (FCFS), and each bus's plan is optimal given what's already locked in, without needing to solve a global combinatorial problem.

I considered ILP and pure FCFS as alternatives. ILP is globally optimal but becomes unworkable once you add non-linear rules (operator fleet scoring is one already). Pure FCFS with fixed plans doesn't let you tune tradeoffs at all. The greedy look-ahead hits the right balance: fast (well under 1ms per bus), tunable, and easy to extend.

---

## Field: "A few brief notes about your build"

A few things worth flagging:

**On the hard constraints** — Range and sequence are checked before simulation, not during. This means infeasible plans are pruned upfront, so the simulator never touches an invalid state. That keeps the logic clean and makes correctness easy to reason about.

**On the soft weights** — Nothing is hardcoded. Weights come from the scenario JSON and are also exposed as live sliders in the UI. Changing a weight is one value in one place; you don't need to touch any Python.

**On extensibility** — Hard constraints and soft scorers are both pluggable interfaces (`HardConstraint`, `SoftScorer`). Adding a new rule is a new class + one line of registration. The core engine doesn't change. I've documented this with concrete examples in `ARCHITECTURE.md`, along with a table of 8 anticipated real-world changes and how the current design handles each one through data alone.

**On the scenarios** — I designed 5 scenarios to stress-test different failure modes: even spacing (baseline), bunched departures (high contention), asymmetric load, operator-priority weighting, and a worst-case convergence where buses from both directions collide at the inner stations simultaneously.

**Assumptions I made** — Charging is atomic (all-or-nothing, no partial charge), travel speed is uniform and fixed per scenario, and buses queue indefinitely rather than rerouting. These are all documented in `ARCHITECTURE.md` under "Architectural Assumptions".
