# ⚡ VoltTransit — Bidirectional Bus Charging Scheduler

VoltTransit is a state-of-the-art simulation, scheduling, and visualization system for managing electric bus fleets and resolving charging station contention. It models bidirectional transit routes with shared intermediate chargers, physical battery range constraints, and FCFS queue scheduling. It includes a beautiful interactive Streamlit dashboard allowing users to select scenarios and dynamically tune optimization weights on the fly.

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher

### Installation & Setup

1. **Clone the repository** (if not already inside it):
   ```bash
   git clone <repo-url>
   cd bus-charging-scheduler
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application Locally

Start the Streamlit development server:
```bash
streamlit run app.py
```
This will automatically open the application in your default web browser (usually at `http://localhost:8501`).

### Running the Validation Tests

Execute our comprehensive correctness validation test suite:
```bash
python -m unittest scheduler.tests
```

---

## ⚙️ How to Tune and Extend

### 1. Changing Scenario Parameters & Adding Stations
All simulation assets—such as station counts, chargers per station, segment distances, fleets, and default weights—are entirely **data-driven** and parsed from scenario JSON configuration files in the `scenarios/` directory.

To add a new station or double chargers at a station, simply modify the `"network"` structure of the desired scenario file:
```json
"stations": [
  {"id": "A", "name": "Station A", "chargers": 2, "charging_time_minutes": 25}
]
```
The scheduling engine and Streamlit UI will instantly pick up the modifications without a single line of code change!

### 2. Tuning Scorer Weights
You can adjust the weights of the soft constraints to produce different schedules:
- **Locally in the UI**: Drag the interactive sliders in the sidebar to re-run the simulation instantly.
- **As defaults in data**: Set the default coefficients inside the `"weights"` dictionary of the scenario's JSON file:
  ```json
  "weights": {
    "individual": 1.0,
    "operator": 2.0,
    "overall": 1.0
  }
  ```

### 3. Adding a New Rule (Extensibility)
VoltTransit is designed with pluggable hard and soft constraint registries. Adding a new rule is as simple as writing a single class and registering it:

1. **Hard Constraints**: Create a subclass of `HardConstraint` in `scheduler/constraints.py` and implement `is_valid`. Then, append it to `self.hard_constraints` in `SchedulerEngine.__init__`.
2. **Soft Scorers**: Create a subclass of `SoftScorer` in `scheduler/scorers.py` and implement `score`. Then, append it to `self.soft_scorers` with its weight in `SchedulerEngine.__init__`.

For a concrete code walkthrough, see [ARCHITECTURE.md](file:///Users/salauddin/Projects/learning/assigments/bus-charging-schuduler/ARCHITECTURE.md).

---

## ☁️ Deploying to Streamlit Community Cloud

Deploying this app is completely free and takes only two clicks:
1. Push this repository to your public GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
3. Click **"New App"**, select this repository, select the `main` branch, set the file path to `app.py`, and click **"Deploy"**!
Streamlit will automatically read `requirements.txt`, install all dependencies, and host your interactive app on a public URL.
