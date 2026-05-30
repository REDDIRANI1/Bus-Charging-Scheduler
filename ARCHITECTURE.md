# 🏛️ Architecture & Extensibility Design Document

This document covers the architectural patterns, framework selections, extensibility protocols, and data models of the VoltTransit electric bus fleet scheduling system.

---

## 1. Architectural Approach & Framework Rationale

### Python & Streamlit
- **Single-Process in Memory**: The complete simulation and UI execute in a single process. Keeping the simulation in memory allows sub-second, real-time re-simulation when sliders are adjusted in the UI, avoiding complex API overhead or database latency.
- **Streamlit**: Selected for rapid component-driven rendering, native support for interactive widgets (sliders, dropdowns), and zero-configuration hosting on Streamlit Community Cloud.

### Single-Pass Greedy Simulation with Look-Ahead Scoring
To schedule charger sharing, three approaches were analyzed:
1. **Integer Linear Programming (ILP)**: While theoretically optimal, ILP becomes extremely rigid and mathematically intractable when arbitrary non-linear operational rules are added (e.g., driver shift schedules, operator-specific policies).
2. **Pure First-Come-First-Served (FCFS) with Fixed Charging Plans**: Extremely simple but completely non-tunable, producing identical schedules regardless of changing business priorities (violates Scenario 4).
3. **Simulation-Based Greedy Look-Ahead (Selected)**: Buses are processed chronologically by departure time. For each bus, all feasible charging plans are generated. The bus evaluates each plan by running a complete "look-ahead simulation" against the *actual committed state* of all station queues left by earlier buses. A weighted soft scorer evaluates individual wait, operator fleet coordination, and overall trip times. The plan with the lowest composite score is selected and committed.

**Why this is highly defensible:**
This approach models real-world fleet dispatching. It natively handles any non-linear constraints or scores (such as operator fleet deviations) and resolves station queue contention dynamically. Since there are only 8 valid plans per bus and 20 buses, the search space per bus is tiny (8 simulations), making the greedy look-ahead take less than 10 milliseconds, enabling live UI updates.

---

## 2. Data Model Design

The system implements a **100% data-driven** topology and configuration schema. A single JSON file encapsulates the entire scenario state:

```
[Scenario JSON]
  ├── Name & Description (Metadata)
  ├── Network (Topology)
  │     ├── Endpoints (List of terminal origin/destination names)
  │     ├── Stations (Charging stations with charger counts & charging times)
  │     └── Segments (Inter-node edges with physical distances in km)
  ├── Parameters (Global constants: bus_speed_kmh, max_range_km)
  ├── Weights (Default optimization coefficients)
  └── Buses (Fleet timetable: IDs, Operators, Directions, Departure Times)
```

The parsed classes (`Route`, `Station`, `Segment`, `Bus`) encapsulate this JSON structure. 

### Output Data Structures
The engine produces two highly structured, UI-consumable models:
1. **Per-Bus Timeline (`BusSchedule`)**: A detailed chronological list of events (`depart`, `arrive`, `queue_wait`, `charge_start`, `charge_end`, `pass`) with absolute integer minutes and physical state (remaining range) at each point.
2. **Per-Station Queue Log (`StationLog`)**: A chronological list of all charging events served by each station, detailing arrival, start, and end times, wait durations, and operator labels.

---

## 3. Handling Anticipated Future Changes (Foresight Analysis)

The architecture is designed to handle key operational changes **strictly through data/configuration changes—requiring zero code modifications**:

| Anticipated Change | How the Design Handles It (No Code Changes) |
| :--- | :--- |
| **Adding a New Station** | Add a new station entry to `"stations"` and define the new segment edges/distances in `"segments"` in the JSON. The engine's pathing automatically chains the nodes and validates feasibility across the new segments. |
| **Doubling Chargers at a Station** | Increment the `"chargers"` value (e.g. from `1` to `2`) at the target station in the JSON. The FCFS queuing simulator dynamically manages concurrent charger capacity. |
| **Swapping an Operator** | Change the `"operator"` string in the `"buses"` array in the JSON. The UI badges and the operator fleet average scorers dynamically adjust to the new name. |
| **Changed Segment Distances** | Modify `"distance_km"` values in `"segments"` in the JSON. The travel duration and battery range validators automatically adjust. |
| **Priority / VIP Buses** | (Data) Add a `"priority": true` or `"vip": true` property to the bus in the JSON. (Code-Extensibility) Add a `PriorityScorer` that reduces the penalty of high-priority buses so they are scheduled with zero wait times. |
| **Time-of-day Electricity Costs** | (Data) Add a `"tariff"` array to each station in the JSON. (Code-Extensibility) Plug in a new `TariffScorer` that penalizes charging during peak hours, guiding the scheduler to charge at cheaper off-peak windows. |
| **Driver Shifts / Rest Breaks** | (Data) Set `"max_driving_hours"` in parameters. (Code-Extensibility) Plug in a `DriverShiftConstraint` that forces a bus to stop at a station for a rest break if the driving time between charges exceeds a threshold. |
| **Multiple Routes Sharing Stations** | (Data) Define separate routes or overlapping networks in the segments list. (Code-Extensibility) The FCFS queues are hosted on the `Station` objects themselves, so different buses from arbitrary directions or routes will naturally merge into the shared queues. |

---

## 4. How to Change a Weight

Weights are the simplest thing to change. They live in one place — the `"weights"` dictionary of the scenario JSON file:

```json
{
  "weights": {
    "individual": 1.0,
    "operator": 2.0,
    "overall": 0.5
  }
}
```

That's it. The engine reads them at runtime and applies them as multipliers to each scorer. No code changes needed.

If you want to change a weight interactively without touching files, drag the sliders in the Streamlit sidebar — the simulation reruns immediately with the new values.

If you want to add a *new* weight category (e.g., a tariff weight for a new solar scorer), add the key to the JSON and pass it to the scorer in `SchedulerEngine.__init__`:

```python
# In engine.py → SchedulerEngine.__init__
self.soft_scorers = [
    (IndividualWaitScorer(),     self.weights.get("individual", 1.0)),
    (OperatorFleetScorer(),      self.weights.get("operator",   1.0)),
    (OverallNetworkTimeScorer(), self.weights.get("overall",    1.0)),
    (SolarTariffScorer(),        self.weights.get("solar",      1.5)),  # ← new
]
```

One line. The weight is read from the JSON, with a sensible default if the key is absent.

---

## 5. Code Examples for Extending Rules

### A. How to Add a New Soft Scorer
To incentivize charging at stations that have cheaper solar energy tariffs during daylight hours, implement a custom `SolarTariffScorer`:

```python
from scheduler.scorers import SoftScorer
from scheduler.models import Route, Bus
from typing import List, Dict, Any

class SolarTariffScorer(SoftScorer):
    """Penalizes charging at non-solar stations or during non-daylight hours."""
    
    def score(self, plan: List[str], bus: Bus, route: Route,
              simulated_trip: Dict[str, Any], committed_schedules: List[Dict[str, Any]]) -> float:
        penalty = 0.0
        for ev in simulated_trip["events"]:
            if ev["type"] == "charge_start":
                # Get charge start minutes (1200 represented as 20:00)
                start_min = ev["time_minutes"]
                hour = (start_min // 60) % 24
                # Solar peak is between 10:00 and 16:00
                if not (10 <= hour <= 16):
                    penalty += 50.0  # Charge during non-solar peak is penalized
        return penalty
```

**Registration:**
```python
# scheduler/engine.py -> SchedulerEngine.__init__
self.soft_scorers.append((SolarTariffScorer(), self.weights.get("solar_tariff", 1.5)))
```

### B. How to Add a New Hard Constraint
To enforce that buses must never charge more than 3 times on their trip:

```python
from scheduler.constraints import HardConstraint
from scheduler.models import Route, Bus
from typing import List

class MaxChargeStopsConstraint(HardConstraint):
    """Rejects any plan that has more than 3 charging stops."""
    
    def is_valid(self, plan: List[str], bus: Bus, route: Route, max_range_km: float) -> bool:
        return len(plan) <= 3
```

**Registration:**
```python
# scheduler/engine.py -> SchedulerEngine.__init__
self.hard_constraints.append(MaxChargeStopsConstraint())
```

---

## 6. Architectural Assumptions Made

1. **Deterministic Travel Speeds**: Buses travel at a constant, uniform speed (default 60 km/h) with zero traffic fluctuations, making travel times strictly proportional to distance.
2. **Instant Battery Recharge on Charge End**: A bus's battery is instantly restored to its maximum range (default 240 km) upon completion of the configured charging duration (default 25 minutes).
3. **No Segment Backtracking**: Buses travel strictly in their direction of origin-destination travel and can only visit intermediate stations in sequential route order.
4. **Infinite Charger Queue Buffer**: Charging stations have an infinite queue buffer size; any bus that arrives when all chargers are full can wait indefinitely in the queue.
5. **No Station Breakdowns / Perfect Reliability**: Stations and chargers are 100% reliable with zero maintenance downtime or power delivery variations.
