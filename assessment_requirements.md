# Take-Home Assignment: Bus Charging Scheduler

## Stack and hosting
Use Python and Streamlit. Everything — scheduling logic, scenario loading, UI — lives in one Python repo, one process.
- Host on Streamlit Community Cloud — free, 2 clicks from GitHub
- Libraries: Any Python library that installs via pip works fine.

## The problem
Electric buses run on a fixed route with 4 charging stations along the way.

**Route:** Bengaluru → A → B → C → D → Kochi
Buses travel in both directions — some go Bengaluru → Kochi, others go Kochi → Bengaluru — and share the same charging stations.

Each bus starts its trip with a full charge — Bengaluru and Kochi have slow chargers that fully charge buses before they depart, so you can assume every bus leaves its origin with a 240 km range. Only A, B, C, and D are scheduling charging stations — the endpoints are not part of the scheduling problem.

Stations exist so buses can recharge along the way. Which stations a bus uses is up to your scheduler, as long as the bus never runs out of range between charges.

Each station has 1 charger, so when multiple buses want to charge at the same station around the same time, the scheduler has to decide who goes first and who waits.

Your job: build the scheduler that decides each bus's charging plan and the order in which buses use the chargers.

## The rules

### Physical constants
- **Battery range:** 240 km on a full charge
- **Charging:** always to full, takes 25 minutes (fixed)
- **All buses travel at the same speed** (no traffic, no variation)

### The route
| Segment | Distance |
| --- | --- |
| Bengaluru → A | 100 km |
| A → B | 120 km |
| B → C | 100 km |
| C → D | 120 km |
| D → Kochi | 100 km |
| **Total** | **540 km** |

Travel time is determined by distance (use a consistent speed in your simulation — e.g. 60 km/h means a 100 km segment takes 100 minutes).

### Buses
- **20 buses total per scenario** — 10 going Bengaluru→Kochi, 10 going Kochi→Bengaluru
- Each bus has a scheduled departure time from its starting end
- Each bus belongs to one of 3 operators: KPN, Freshbus, Flixbus

### Charging plans
A bus can drive a maximum of 240 km on a full charge. Charging always fills the battery back to full.

This means between any two consecutive charges — or between starting and the first charge, or between the last charge and arrival — a bus cannot travel more than 240 km. If it would, the schedule is invalid.

This means a bus going Bengaluru → Kochi cannot complete the trip without charging at least 2 times (total trip is 540 km). The scheduler chooses which 2 (or more) stations the bus uses.

### Hard rules that must always hold
- One bus per charger at a time (1 charger per station)
- Charging is always exactly 25 minutes
- A bus must never run out of range between two consecutive charges (or between segments without a charge)
- A bus visits stations in route order — no backtracking

### What to optimize for
When the scheduler has flexibility (which stations to use, who charges first), it should weigh three soft rules:
1. **Individual bus** — no single bus should wait too long
2. **Operator** — each operator's fleet should run smoothly as a group
3. **Overall** — total time across the whole network should be low

These weights should be tunable — engineers will change them as we learn what matters operationally. Don't hardcode them.

### What to build
A single Python + Streamlit app that:

**The scheduler**
- Reads any scenario from your data files
- Uses your framework, with weights from the scenario
- Decides each bus's charging plan (which stations it uses) and the order in which buses use each station
- Computes, for each bus, the timeline: when it charges where, how long it waits, when it arrives at Kochi or Bengaluru

**The UI**
- A dropdown at the top to pick a scenario
- A scenario view showing the input (raw data or readable table) so reviewers can see what's being fed in
- A per-bus timetable — for each bus, show its full timeline: charging stations used, time at each, wait (if any), final arrival
- A per-station view — for each of A, B, C, D, show the order in which buses charged there

No metrics dashboards, no maps, no animations. Pick a scenario → see the input → see what the scheduler decided.
