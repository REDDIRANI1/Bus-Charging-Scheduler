import streamlit as st
import json
import os
import pandas as pd
from typing import Dict, Any, List

from scheduler.models import Route, Station, Segment, Bus, time_to_minutes, minutes_to_time
from scheduler.engine import SchedulerEngine

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VoltTransit — Bus Charging Scheduler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# Minimal CSS: font + spacing only, no complex custom classes
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .block-container { max-width: 1400px !important; padding: 2rem 3rem 4rem 3rem !important; }
    h1 { font-size: 2.6rem !important; font-weight: 800 !important; letter-spacing: -0.03em !important; }
    h2 { font-size: 1.7rem !important; font-weight: 700 !important; }
    h3 { font-size: 1.35rem !important; font-weight: 700 !important; }
    p, li { font-size: 1.05rem !important; }
    .stTabs [data-baseweb="tab"] { font-size: 1.05rem !important; font-weight: 600 !important; padding: 0.75rem 1.5rem !important; }
    .stSelectbox label, .stMultiSelect label, .stTextInput label, .stSlider label { font-size: 1rem !important; font-weight: 600 !important; }
    .stDataFrame { font-size: 1rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────
SCENARIOS_DIR = "scenarios"


@st.cache_data
def list_available_scenarios() -> List[str]:
    if not os.path.exists(SCENARIOS_DIR):
        return []
    return sorted(f for f in os.listdir(SCENARIOS_DIR) if f.endswith(".json"))


def load_scenario(filename: str) -> Dict[str, Any]:
    with open(os.path.join(SCENARIOS_DIR, filename), "r") as f:
        return json.load(f)


OP_COLORS = {
    "kpn":      ("🟣", "#a5b4fc"),
    "freshbus": ("🟢", "#6ee7b7"),
    "flixbus":  ("🟡", "#fde68a"),
}

def op_icon(op: str) -> str:
    return OP_COLORS.get(op.lower(), ("⚪", "#cbd5e1"))[0]

def op_color(op: str) -> str:
    return OP_COLORS.get(op.lower(), ("⚪", "#cbd5e1"))[1]


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
st.title("⚡ VoltTransit — Bus Charging Scheduler")
st.markdown("**Bidirectional route:** Bengaluru ↔ Kochi · 540 km · 4 intermediate charging stations (A, B, C, D)")
st.divider()

# ─────────────────────────────────────────────────────────────
# SCENARIO PICKER (spec: must be at top)
# ─────────────────────────────────────────────────────────────
scenarios = list_available_scenarios()
if not scenarios:
    st.error("No scenario files found in `scenarios/` directory.")
    st.stop()

selected_file = st.selectbox(
    "🗂️ Select Scenario",
    scenarios,
    format_func=lambda x: x.replace(".json", "").replace("_", " ").title(),
)
scenario_data = load_scenario(selected_file)

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Configuration")

default_weights = scenario_data.get("weights", {"individual": 1.0, "operator": 1.0, "overall": 1.0})

st.sidebar.subheader("🎛️ Optimization Weights")
st.sidebar.caption("Adjust to re-simulate schedules in real time.")
w_individual = st.sidebar.slider("Individual Bus Wait",     0.0, 5.0, float(default_weights.get("individual", 1.0)), 0.1)
w_operator   = st.sidebar.slider("Operator Coordination",   0.0, 5.0, float(default_weights.get("operator",   1.0)), 0.1)
w_overall    = st.sidebar.slider("Overall Network Time",    0.0, 5.0, float(default_weights.get("overall",    1.0)), 0.1)

st.sidebar.divider()
st.sidebar.subheader("📐 Physical Constants")
params = scenario_data.get("parameters", {"bus_speed_kmh": 60, "max_range_km": 240})
bus_speed = params.get("bus_speed_kmh", 60)
max_range = params.get("max_range_km", 240)
st.sidebar.markdown(f"🚌 **Speed:** {bus_speed} km/h")
st.sidebar.markdown(f"🔋 **Battery range:** {max_range} km")
st.sidebar.markdown(f"⏱️ **Charge time:** 25 min (always full)")

st.sidebar.divider()
st.sidebar.subheader("📊 Active Weights")
st.sidebar.markdown(f"- Individual: **{w_individual:.1f}**")
st.sidebar.markdown(f"- Operator: **{w_operator:.1f}**")
st.sidebar.markdown(f"- Overall: **{w_overall:.1f}**")

# ─────────────────────────────────────────────────────────────
# BUILD ROUTE & RUN ENGINE
# ─────────────────────────────────────────────────────────────
network   = scenario_data["network"]
endpoints = network["endpoints"]

stations_list = [
    Station(s["id"], s["name"], s["chargers"], s["charging_time_minutes"])
    for s in network["stations"]
]
segments_list = [
    Segment(seg["from"], seg["to"], seg["distance_km"])
    for seg in network["segments"]
]
route = Route(endpoints, stations_list, segments_list)

buses = [
    Bus(b["id"], b["operator"], b["direction"], b["departure"])
    for b in scenario_data["buses"]
]

engine    = SchedulerEngine(route, params, {"individual": w_individual, "operator": w_operator, "overall": w_overall})
schedules = engine.schedule_all(buses)

# ─────────────────────────────────────────────────────────────
# SCENARIO INFO + KPI SUMMARY
# ─────────────────────────────────────────────────────────────
st.subheader(scenario_data["name"])
st.markdown(scenario_data["description"])

# KPIs using native st.metric
total_buses = len(schedules)
bk = sum(1 for s in schedules if s["direction"].endswith("Kochi"))
kb = total_buses - bk
avg_trip   = sum(s["total_trip_minutes"]  for s in schedules) / max(total_buses, 1)
total_wait = sum(s["total_wait_minutes"]  for s in schedules)
max_wait   = max(s["total_wait_minutes"]  for s in schedules)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🚌 Total Buses",   total_buses)
k2.metric("➡️ B→K / ⬅️ K→B", f"{bk} / {kb}")
k3.metric("⏱️ Avg Trip",      f"{avg_trip:.0f} min")
k4.metric("⏳ Total Wait",    f"{total_wait} min")
k5.metric("🔴 Max Bus Wait",  f"{max_wait} min")

# Route diagram (pure text)
st.divider()
st.caption("Route map:")
route_parts = []
for i, node in enumerate(route.nodes_sequence):
    if node in endpoints:
        route_parts.append(f"**{node}**")
    else:
        stn = route.stations[node]
        served = len(stn.committed_events)
        route_parts.append(f"🔋 **{node}** ({stn.name}, {served} buses)")
    if i < len(route.nodes_sequence) - 1:
        dist = route.get_distance(route.nodes_sequence[i], route.nodes_sequence[i + 1])
        route_parts.append(f"──{int(dist)}km──")

st.markdown("  ".join(route_parts))
st.divider()

# ─────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🕒 Per-Bus Timetable",
    "🚉 Per-Station Queues",
    "📁 Scenario Inputs",
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 — PER-BUS TIMETABLE
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📊 All Bus Schedules")
    st.markdown("Every bus's departure, arrival, total trip time, wait time, and which stations it charged at.")

    # Filters
    with st.expander("🔍 Filter Buses", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            search_bus = st.text_input("Search Bus ID", "", placeholder="e.g. BK-01").strip().upper()
        with fc2:
            ops_all = sorted(set(s["operator"] for s in schedules))
            sel_ops = st.multiselect("Operator", ops_all, default=ops_all)
        with fc3:
            dirs_all = sorted(set(s["direction"] for s in schedules))
            sel_dirs = st.multiselect("Direction", dirs_all, default=dirs_all)

    filtered = [
        s for s in schedules
        if search_bus in s["bus_id"].upper()
        and s["operator"] in sel_ops
        and s["direction"] in sel_dirs
    ]

    # Summary table
    if filtered:
        rows = []
        for s in filtered:
            wait_flag = "⚠️" if s["total_wait_minutes"] > 0 else "✅"
            rows.append({
                "Bus ID":        s["bus_id"],
                "Operator":      f"{op_icon(s['operator'])} {s['operator']}",
                "Direction":     s["direction"],
                "Depart":        s["departure_time"],
                "Arrive":        s["arrival_time"],
                "Trip (min)":    s["total_trip_minutes"],
                "Wait (min)":    s["total_wait_minutes"],
                "Status":        wait_flag,
                "Charging Stops": ", ".join(s["charging_plan"]) if s["charging_plan"] else "—",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=min(len(rows) * 42 + 60, 700))
    else:
        st.info("No buses match the chosen filters.")

    st.divider()

    # ── Journey detail ─────────────────────────────────────────
    st.subheader("🗺️ Journey Path Detail")
    st.markdown("Select a bus to see its full step-by-step timeline — when it departs, arrives at each station, charges, and waits in queue.")

    bus_ids = [s["bus_id"] for s in filtered]
    if not bus_ids:
        st.info("No buses to display — adjust filters above.")
    else:
        sel_bus = st.selectbox("Select Bus", bus_ids, key="bus_detail")
        bus_s   = next(s for s in schedules if s["bus_id"] == sel_bus)

        # Bus summary row
        ic = op_icon(bus_s["operator"])
        c_a, c_b, c_c, c_d = st.columns(4)
        c_a.metric("Operator",       f"{ic} {bus_s['operator']}")
        c_b.metric("Direction",      bus_s["direction"])
        c_c.metric("Total Trip",     f"{bus_s['total_trip_minutes']} min")
        c_d.metric("Total Wait",     f"{bus_s['total_wait_minutes']} min")

        stops_str = ", ".join(bus_s["charging_plan"]) if bus_s["charging_plan"] else "None"
        st.markdown(f"**Charging stops:** {stops_str}")
        st.markdown("---")

        # Legend caption
        st.caption("🟢 Depart  ·  🔵 Arrive  ·  🔋 Charging  ·  🟠 Queue Wait  ·  ⏭️ Passed")

        # Timeline — each event as a native st.markdown row
        for ev in bus_s["events"]:
            t   = ev["type"]
            loc = ev.get("location", "")
            ts  = ev.get("time", "")

            if t == "depart":
                st.markdown(f"🟢 &nbsp; **Departed {loc}** at `{ts}` &nbsp;·&nbsp; Range: {ev.get('range_km')} km")
            elif t == "arrive":
                st.markdown(f"🔵 &nbsp; **Arrived at {loc}** at `{ts}` &nbsp;·&nbsp; Range: {ev.get('range_km')} km")
            elif t == "queue_wait" and ev.get("wait_minutes", 0) > 0:
                st.warning(f"🟠  Queued at **{loc}** — waited **{ev['wait_minutes']} min** for charger to free up")
            elif t == "charge_start":
                st.markdown(f"🔋 &nbsp; **Started charging** at Station {loc} at `{ts}`")
            elif t == "charge_end":
                st.markdown(f"✅ &nbsp; **Finished charging** at `{ts}` — battery restored to {ev.get('range_km')} km")
            elif t == "pass":
                st.markdown(f"⏭️ &nbsp; Passed Station {loc} at `{ts}` — Range: {ev.get('range_km')} km *(no charge needed)*")


# ═══════════════════════════════════════════════════════════════
# TAB 2 — PER-STATION QUEUES
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🚉 Charging Station Activity")
    st.markdown("For each of the 4 stations (A, B, C, D), see every bus that charged there — the order, exact times, and how long each waited.")

    station_items = list(route.stations.items())
    c1, c2 = st.columns(2, gap="large")

    for idx, (sid, stn) in enumerate(station_items):
        col = c1 if idx % 2 == 0 else c2
        with col:
            total_w = sum(ev["wait_minutes"] for ev in stn.committed_events)
            n_waited = sum(1 for ev in stn.committed_events if ev["wait_minutes"] > 0)

            st.markdown(f"### 🔋 Station {sid} — {stn.name}")

            m1, m2, m3 = st.columns(3)
            m1.metric("Chargers",    stn.chargers)
            m2.metric("Buses Served", len(stn.committed_events))
            m3.metric("Total Wait",  f"{total_w} min")

            if not stn.committed_events:
                st.info("No buses charged at this station.")
            else:
                st.markdown(f"**Charge order** ({n_waited} bus{'es' if n_waited != 1 else ''} had to wait):")

                for i, ev in enumerate(stn.committed_events):
                    icon = op_icon(ev["operator"])
                    arr  = minutes_to_time(ev["arrival_time"])
                    cs   = minutes_to_time(ev["charge_start"])
                    ce   = minutes_to_time(ev["charge_end"])
                    wait = ev["wait_minutes"]

                    with st.container(border=True):
                        r1, r2 = st.columns([2, 1])
                        with r1:
                            st.markdown(f"**#{i+1} &nbsp; {ev['bus_id']}** &nbsp; {icon} {ev['operator']}")
                            st.caption(f"Arrived: {arr}  ·  Charged: {cs} → {ce}")
                        with r2:
                            if wait > 0:
                                st.warning(f"⏳ Waited {wait} min")
                            else:
                                st.success("✓ No Wait")

            st.divider()


# ═══════════════════════════════════════════════════════════════
# TAB 3 — SCENARIO INPUTS
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📁 Scenario Input Data")
    st.markdown("The raw data fed into the scheduler — network topology, physical parameters, optimization weights, and the bus departure timetable.")

    c_l, c_r = st.columns(2, gap="large")

    with c_l:
        st.markdown("#### 🌐 Network, Parameters & Weights")
        st.json({
            "name":        scenario_data["name"],
            "description": scenario_data["description"],
            "network": {
                "endpoints": scenario_data["network"]["endpoints"],
                "stations":  scenario_data["network"]["stations"],
                "segments":  scenario_data["network"]["segments"],
            },
            "parameters": scenario_data["parameters"],
            "weights":    scenario_data["weights"],
        })

    with c_r:
        st.markdown("#### 🚌 Fleet Departure Timetable")
        bus_rows = [
            {
                "Bus ID":    b["id"],
                "Operator":  f"{op_icon(b['operator'])} {b['operator']}",
                "Direction": b["direction"],
                "Departure": b["departure"],
            }
            for b in scenario_data["buses"]
        ]
        st.dataframe(
            pd.DataFrame(bus_rows),
            use_container_width=True,
            hide_index=True,
            height=min(len(bus_rows) * 42 + 60, 700),
        )
