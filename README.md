# ⚡ VoltTransit — Bus Charging Scheduler

This is my take-home submission for the SDE assessment. I built a scheduling engine for electric buses running a bidirectional route between Bengaluru and Kochi, with 4 shared charging stations along the way.

The core challenge was making sure every bus gets a valid charging plan — never running out of battery, always visiting stations in travel order — while also resolving contention when multiple buses want to charge at the same station around the same time.

## 🔗 Live App

👉 **[Open on Streamlit Cloud](https://bus-charging-scheduler-u3xxexqnln9i6mbxvav4i6.streamlit.app/)**

---

## What I Built

**The Scheduler** (`scheduler/` folder)

The engine works by generating all physically valid charging plans for each bus (combinations of stations that satisfy the range and sequence constraints), simulating each plan against the current queue state, scoring them using three soft metrics, and committing the best one. Buses are processed in departure-time order so earlier buses get priority — which naturally implements FCFS without any special-casing.

The three soft metrics — individual wait time, operator fleet consistency, and overall network time — each plug in as independent `SoftScorer` classes. Their weights come from the scenario file (or the sidebar sliders in the UI), so nothing is hardcoded.

Hard constraints (range and no-backtracking) and soft scorers are both pluggable interfaces. Adding a new rule is just writing a new class — no changes to the core engine.

**The UI** (`app.py`)

A Streamlit dashboard with three tabs:
- **Per-Bus Timetable** — see every bus's departure, charging stops, wait times, and final arrival
- **Per-Station Queues** — see the exact order buses charged at each of the 4 stations, with timestamps and wait times
- **Scenario Inputs** — the raw JSON config and fleet departure table, so reviewers can see exactly what went in

The sidebar has sliders to tune the 3 weights live — the simulation reruns instantly as you drag them.

**The Scenarios** (`scenarios/` folder)

5 scenarios to test different real-world conditions:
1. **Even Spacing** — baseline, buses every 15 minutes
2. **Bunched Start** — many buses departing close together (high contention)
3. **Asymmetric Load** — more buses in one direction than the other
4. **Operator-Heavy** — operator coordination weight cranked up
5. **Worst Case Convergence** — buses converging on stations simultaneously from both directions

---

## Running It Locally

```bash
# Clone and enter the repo
git clone https://github.com/REDDIRANI1/Bus-Charging-Scheduler.git
cd Bus-Charging-Scheduler

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (just streamlit and pandas)
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Opens at `http://localhost:8501`.

To run the test suite (validates all 5 scenarios against all 4 hard rules):
```bash
python -m unittest scheduler.tests
```

---

## Repo Structure

```
├── app.py                  # Streamlit UI
├── scheduler/
│   ├── engine.py           # Core scheduling logic
│   ├── constraints.py      # Hard constraint interfaces + implementations
│   ├── scorers.py          # Soft scorer interfaces + implementations
│   └── models.py           # Route, Bus, Station data structures
├── scenarios/              # 5 scenario JSON files
├── requirements.txt
├── ARCHITECTURE.md         # Design decisions and extensibility guide
└── assessment_requirements.md  # Full PDF requirements in markdown
```

---

## Extending It

To add a new station — just add it to the `"stations"` and `"segments"` arrays in any scenario JSON. The engine picks it up automatically.

To add a new scheduling rule — subclass `HardConstraint` or `SoftScorer` in the relevant file, implement the single required method, and register it in `SchedulerEngine.__init__`. That's it.

For more detail on the design decisions, see [ARCHITECTURE.md](ARCHITECTURE.md).

