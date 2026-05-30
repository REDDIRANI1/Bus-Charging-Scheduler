import streamlit as st
import json
import os
import pandas as pd
from typing import Dict, Any, List

from scheduler.models import Route, Station, Segment, Bus, time_to_minutes, minutes_to_time
from scheduler.engine import SchedulerEngine

# -------------------------------------------------------------
# Page Config
# -------------------------------------------------------------
st.set_page_config(
    page_title="VoltTransit — Bus Charging Scheduler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------
# CSS — focus: readability, large text, clear structure
# -------------------------------------------------------------
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
    /* === GLOBAL === */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        letter-spacing: -0.02em;
    }

    /* Wider content area */
    .block-container {
        max-width: 1400px !important;
        padding: 2.5rem 3rem 4rem 3rem !important;
    }

    /* === MAKE ALL STREAMLIT TEXT BIGGER === */
    .stMarkdown p, .stMarkdown li { font-size: 1.05rem !important; line-height: 1.7 !important; }
    .stSelectbox label, .stMultiSelect label, .stTextInput label, .stSlider label {
        font-size: 1rem !important;
        font-weight: 600 !important;
    }

    /* Bigger tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 0.25rem; }
    .stTabs [data-baseweb="tab"] {
        padding: 0.85rem 1.75rem !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }

    /* Bigger dataframes */
    .stDataFrame { font-size: 1rem !important; }
    .stDataFrame td, .stDataFrame th { padding: 0.6rem 0.75rem !important; }

    /* === HERO HEADER === */
    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        padding: 2.5rem 3rem;
        border-radius: 20px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(99, 102, 241, 0.15);
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
    }
    .hero h1 {
        font-size: 2.8rem !important;
        font-weight: 900 !important;
        margin: 0 !important;
        background: linear-gradient(135deg, #a5b4fc, #818cf8, #38bdf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }
    .hero-sub {
        color: #94a3b8;
        font-size: 1.15rem;
        margin-top: 0.4rem;
    }
    .hero-route {
        display: inline-block;
        margin-top: 0.8rem;
        padding: 0.4rem 1.1rem;
        border-radius: 100px;
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.25);
        color: #a5b4fc;
        font-size: 0.9rem;
        font-weight: 600;
    }

    /* === SCENARIO BANNER === */
    .scenario-banner {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.1);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.75rem;
    }
    .scenario-banner h2 {
        margin: 0 0 0.3rem 0 !important;
        font-size: 1.6rem !important;
        color: #f1f5f9;
    }
    .scenario-banner p {
        margin: 0 !important;
        color: #94a3b8;
        font-size: 1.05rem !important;
    }

    /* === KPI ROW === */
    .kpi-row {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 1rem;
        margin-bottom: 2rem;
    }
    @media (max-width: 900px) {
        .kpi-row { grid-template-columns: repeat(2, 1fr); }
    }
    .kpi {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
    }
    .kpi-num {
        font-size: 2.2rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.1;
        margin-bottom: 0.25rem;
    }
    .kpi-num.c1 { color: #818cf8; }
    .kpi-num.c2 { color: #22d3ee; }
    .kpi-num.c3 { color: #34d399; }
    .kpi-num.c4 { color: #fbbf24; }
    .kpi-num.c5 { color: #fb7185; }
    .kpi-lbl {
        font-size: 0.78rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }

    /* === ROUTE MAP === */
    .route-map {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0;
        padding: 1.5rem 0 0.5rem 0;
        flex-wrap: wrap;
    }
    .rm-node {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.4rem;
    }
    .rm-circle {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 0.85rem;
        font-family: 'JetBrains Mono', monospace;
    }
    .rm-circle.ep {
        background: linear-gradient(135deg, #6366f1, #818cf8);
        color: #fff;
        box-shadow: 0 0 14px rgba(99, 102, 241, 0.3);
    }
    .rm-circle.st { background: #1e293b; border: 2px solid #475569; color: #cbd5e1; }
    .rm-circle.st.active { border-color: #22d3ee; color: #22d3ee; box-shadow: 0 0 10px rgba(34,211,238,0.2); }
    .rm-name {
        font-size: 0.72rem;
        color: #94a3b8;
        font-weight: 600;
        text-align: center;
        max-width: 75px;
        line-height: 1.15;
    }
    .rm-edge {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin: 0 0.2rem;
    }
    .rm-line { width: 60px; height: 2px; background: #334155; }
    .rm-dist {
        font-size: 0.65rem;
        color: #64748b;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 2px;
    }

    /* === OPERATOR BADGES === */
    .op { padding: 0.25rem 0.7rem; border-radius: 100px; font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; display: inline-block; }
    .op-kpn { background: rgba(129,140,248,0.12); color: #a5b4fc; border: 1px solid rgba(129,140,248,0.3); }
    .op-freshbus { background: rgba(52,211,153,0.12); color: #6ee7b7; border: 1px solid rgba(52,211,153,0.3); }
    .op-flixbus { background: rgba(251,191,36,0.12); color: #fde68a; border: 1px solid rgba(251,191,36,0.3); }
    .op-other { background: rgba(148,163,184,0.12); color: #cbd5e1; border: 1px solid rgba(148,163,184,0.3); }

    /* === TIMELINE === */
    .tl { margin: 1rem 0 2rem 0; padding-left: 0.5rem; }
    .tl-ev {
        position: relative;
        padding: 0.9rem 0 1rem 2.75rem;
        border-left: 3px solid #1e293b;
    }
    .tl-ev:last-child { border-left-color: transparent; }
    .tl-ev::before {
        content: '';
        position: absolute;
        left: -9px;
        top: 1.1rem;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #1e293b;
        border: 3px solid #334155;
    }
    .tl-ev.ev-depart::before  { background: #10b981; border-color: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.5); }
    .tl-ev.ev-arrive::before  { background: #3b82f6; border-color: #3b82f6; box-shadow: 0 0 8px rgba(59,130,246,0.5); }
    .tl-ev.ev-wait::before    { background: #f97316; border-color: #f97316; box-shadow: 0 0 8px rgba(249,115,22,0.5); }
    .tl-ev.ev-charge::before  { background: #06b6d4; border-color: #06b6d4; box-shadow: 0 0 8px rgba(6,182,212,0.5); }
    .tl-ev.ev-pass::before    { background: #475569; border-color: #475569; }
    .tl-title { font-weight: 700; font-size: 1.1rem; color: #f1f5f9; margin-bottom: 0.1rem; }
    .tl-desc { font-size: 0.95rem; color: #94a3b8; }

    /* === STATION CARD === */
    .stn-card {
        background: rgba(15, 23, 42, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
    }
    .stn-top {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.25rem;
    }
    .stn-icon {
        width: 56px; height: 56px;
        border-radius: 14px;
        background: linear-gradient(135deg, #1e293b, #334155);
        border: 1px solid #475569;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.4rem; font-weight: 800; color: #22d3ee;
        font-family: 'JetBrains Mono', monospace;
    }
    .stn-stats {
        display: flex;
        gap: 2rem;
        margin-bottom: 1.25rem;
        flex-wrap: wrap;
    }
    .stn-stat-label { font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; }
    .stn-stat-val { font-size: 1.6rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; color: #e2e8f0; }
    .stn-stat-val.teal { color: #22d3ee; }
    .stn-stat-val.purple { color: #a5b4fc; }
    .stn-stat-val.amber { color: #fbbf24; }

    /* Queue item */
    .qi {
        background: rgba(30, 41, 59, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 14px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.65rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
    }
    .qi:hover { border-color: rgba(99, 102, 241, 0.15); }
    .qi-bus { font-weight: 700; font-size: 1.05rem; color: #f1f5f9; font-family: 'JetBrains Mono', monospace; }
    .qi-time { font-size: 0.92rem; color: #94a3b8; margin-top: 0.15rem; }
    .qi-time b { color: #e2e8f0; }
    .qi-ok { color: #34d399; font-weight: 700; font-size: 0.9rem; }
    .qi-wait { color: #f97316; font-weight: 700; font-size: 0.9rem; }

    /* === SIDEBAR === */
    section[data-testid="stSidebar"] > div { padding-top: 2rem; }
    .sb-card {
        background: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
    }
    .sb-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.55rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .sb-row:last-child { border-bottom: none; }
    .sb-lbl { color: #94a3b8; font-size: 0.9rem; }
    .sb-val { color: #22d3ee; font-weight: 700; font-size: 1.05rem; font-family: 'JetBrains Mono', monospace; }

    /* === LEGEND === */
    .legend-bar {
        display: flex; gap: 1.25rem; flex-wrap: wrap;
        padding: 0.85rem 1.25rem;
        background: rgba(30,41,59,0.3);
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.04);
        margin-bottom: 0.75rem;
    }
    .lg-i { display: flex; align-items: center; gap: 0.45rem; font-size: 0.85rem; color: #94a3b8; }
    .lg-dot { width: 11px; height: 11px; border-radius: 50%; flex-shrink: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------
# Data Loading
# -------------------------------------------------------------
SCENARIOS_DIR = "scenarios"


@st.cache_data
def list_available_scenarios() -> List[str]:
    """List all scenario configuration files sorted."""
    if not os.path.exists(SCENARIOS_DIR):
        return []
    return sorted(f for f in os.listdir(SCENARIOS_DIR) if f.endswith(".json"))


def load_scenario(filename: str) -> Dict[str, Any]:
    """Load scenario data from JSON file."""
    with open(os.path.join(SCENARIOS_DIR, filename), "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <h1>⚡ VoltTransit</h1>
        <div class="hero-sub">Bidirectional Bus Charging Scheduler</div>
        <div class="hero-route">Bengaluru ↔ Kochi · 540 km · 4 Stations</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# SCENARIO PICKER (top of page per spec)
# ─────────────────────────────────────────────────────────────
scenarios = list_available_scenarios()
if not scenarios:
    st.error("No scenario files found in `scenarios/` directory.")
    st.stop()

selected_file = st.selectbox(
    "🗂️  Select Scenario",
    scenarios,
    format_func=lambda x: x.replace(".json", "").replace("_", " ").title(),
)
scenario_data = load_scenario(selected_file)

# ─────────────────────────────────────────────────────────────
# SIDEBAR — Weights & Params
# ─────────────────────────────────────────────────────────────
st.sidebar.markdown("## ⚙️ Configuration")

default_weights = scenario_data.get("weights", {"individual": 1.0, "operator": 1.0, "overall": 1.0})

st.sidebar.markdown("### 🎛️ Optimization Weights")
st.sidebar.caption("Adjust to re-simulate schedules in real time.")

w_individual = st.sidebar.slider(
    "Individual Bus Wait",
    0.0, 5.0, float(default_weights.get("individual", 1.0)), 0.1,
    help="Higher = penalize long waits for individual buses.",
)
w_operator = st.sidebar.slider(
    "Operator Fleet Coordination",
    0.0, 5.0, float(default_weights.get("operator", 1.0)), 0.1,
    help="Higher = keep same-operator trip times cohesive.",
)
w_overall = st.sidebar.slider(
    "Overall Network Time",
    0.0, 5.0, float(default_weights.get("overall", 1.0)), 0.1,
    help="Higher = minimize total travel time across all buses.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📐 Physical Constants")

params = scenario_data.get("parameters", {"bus_speed_kmh": 60, "max_range_km": 240})
bus_speed = params.get("bus_speed_kmh", 60)
max_range = params.get("max_range_km", 240)

st.sidebar.markdown(
    f"""
    <div class="sb-card">
        <div class="sb-row"><span class="sb-lbl">Travel Speed</span><span class="sb-val">{bus_speed} km/h</span></div>
        <div class="sb-row"><span class="sb-lbl">Battery Range</span><span class="sb-val">{max_range} km</span></div>
        <div class="sb-row"><span class="sb-lbl">Charge Duration</span><span class="sb-val">25 min</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("### 📊 Active Weights")
st.sidebar.markdown(
    f"""
    <div class="sb-card">
        <div class="sb-row"><span class="sb-lbl">Individual</span><span class="sb-val">{w_individual:.1f}</span></div>
        <div class="sb-row"><span class="sb-lbl">Operator</span><span class="sb-val">{w_operator:.1f}</span></div>
        <div class="sb-row"><span class="sb-lbl">Overall</span><span class="sb-val">{w_overall:.1f}</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# BUILD ROUTE & RUN SCHEDULER
# ─────────────────────────────────────────────────────────────
network = scenario_data["network"]
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

engine = SchedulerEngine(route, params, {"individual": w_individual, "operator": w_operator, "overall": w_overall})
schedules = engine.schedule_all(buses)

# ─────────────────────────────────────────────────────────────
# SCENARIO BANNER + ROUTE MAP + KPI
# ─────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="scenario-banner">
        <h2>{scenario_data['name']}</h2>
        <p>{scenario_data['description']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Route map
route_html = '<div class="route-map">'
for i, node in enumerate(route.nodes_sequence):
    is_ep = node in endpoints
    is_stn = node in route.stations
    active = is_stn and len(route.stations[node].committed_events) > 0

    if is_ep:
        route_html += f'<div class="rm-node"><div class="rm-circle ep">{node[:3]}</div><div class="rm-name">{node}</div></div>'
    else:
        act = " active" if active else ""
        route_html += f'<div class="rm-node"><div class="rm-circle st{act}">{node}</div><div class="rm-name">{route.stations[node].name}</div></div>'

    if i < len(route.nodes_sequence) - 1:
        dist = route.get_distance(route.nodes_sequence[i], route.nodes_sequence[i + 1])
        route_html += f'<div class="rm-edge"><div class="rm-line"></div><div class="rm-dist">{int(dist)} km</div></div>'

route_html += "</div>"
st.markdown(route_html, unsafe_allow_html=True)

# KPIs
total_buses = len(schedules)
bk = sum(1 for s in schedules if "Kochi" in s["direction"].split("→")[-1] if "→" in s["direction"])
kb = total_buses - bk
avg_trip = sum(s["total_trip_minutes"] for s in schedules) / max(total_buses, 1)
total_wait = sum(s["total_wait_minutes"] for s in schedules)
max_wait_bus = max(schedules, key=lambda s: s["total_wait_minutes"])

st.markdown(
    f"""
    <div class="kpi-row">
        <div class="kpi"><div class="kpi-num c1">{total_buses}</div><div class="kpi-lbl">Total Buses</div></div>
        <div class="kpi"><div class="kpi-num c2">{bk} / {kb}</div><div class="kpi-lbl">B→K / K→B</div></div>
        <div class="kpi"><div class="kpi-num c3">{avg_trip:.0f} min</div><div class="kpi-lbl">Avg Trip</div></div>
        <div class="kpi"><div class="kpi-num c4">{total_wait} min</div><div class="kpi-lbl">Total Wait</div></div>
        <div class="kpi"><div class="kpi-num c5">{max_wait_bus['total_wait_minutes']} min</div><div class="kpi-lbl">Max Wait ({max_wait_bus['bus_id']})</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🕒  Per-Bus Timetable", "🚉  Per-Station Queues", "📁  Scenario Inputs"])


def op_badge(op: str) -> str:
    lo = op.lower()
    if "kpn" in lo:
        return f'<span class="op op-kpn">{op}</span>'
    if "fresh" in lo:
        return f'<span class="op op-freshbus">{op}</span>'
    if "flix" in lo:
        return f'<span class="op op-flixbus">{op}</span>'
    return f'<span class="op op-other">{op}</span>'


# ═══════════ TAB 1 — PER-BUS TIMETABLE ═══════════
with tab1:
    st.markdown("### 📊 All Bus Schedules")
    st.markdown("Each row shows one bus's full schedule — departure, arrival, trip duration, charging wait, and which stations it stopped at.")
    st.markdown("")

    # Filters in an expander to save space
    with st.expander("🔍 Filter Buses", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            search_bus = st.text_input("Search Bus ID", "", placeholder="e.g. BK-01").strip().upper()
        with fc2:
            operators = sorted(set(s["operator"] for s in schedules))
            selected_op = st.multiselect("Operator", operators, default=operators)
        with fc3:
            directions = sorted(set(s["direction"] for s in schedules))
            selected_dir = st.multiselect("Direction", directions, default=directions)

    filtered = [
        s for s in schedules
        if search_bus in s["bus_id"].upper()
        and s["operator"] in selected_op
        and s["direction"] in selected_dir
    ]

    # Build table
    rows = []
    for s in filtered:
        rows.append({
            "Bus ID": s["bus_id"],
            "Operator": s["operator"],
            "Direction": s["direction"],
            "Depart": s["departure_time"],
            "Arrive": s["arrival_time"],
            "Trip (min)": s["total_trip_minutes"],
            "Wait (min)": s["total_wait_minutes"],
            "Charging Stops": ", ".join(s["charging_plan"]) if s["charging_plan"] else "—",
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=min(len(rows) * 42 + 60, 700))
    else:
        st.info("No buses match the chosen filters.")

    # Journey detail
    st.markdown("---")
    st.markdown("### 🗺️ Journey Path Detail")
    st.markdown("Select a bus below to see its full step-by-step journey with charging events and wait times.")

    bus_ids = [s["bus_id"] for s in filtered]
    if bus_ids:
        sel_bus = st.selectbox("Select Bus", bus_ids, key="bus_detail")
        bus_s = next(s for s in schedules if s["bus_id"] == sel_bus)

        # Info bar
        badge = op_badge(bus_s["operator"])
        st.markdown(
            f'<div style="font-size:1.1rem; color:#94a3b8; margin-bottom:0.5rem;">'
            f'Direction: <b style="color:#e2e8f0">{bus_s["direction"]}</b> &nbsp;·&nbsp; '
            f'Operator: {badge} &nbsp;·&nbsp; '
            f'Trip: <b style="color:#22d3ee">{bus_s["total_trip_minutes"]} min</b> &nbsp;·&nbsp; '
            f'Total Wait: <b style="color:#fbbf24">{bus_s["total_wait_minutes"]} min</b> &nbsp;·&nbsp; '
            f'Stops: <b style="color:#a5b4fc">{", ".join(bus_s["charging_plan"]) or "None"}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Legend
        st.markdown(
            """
            <div class="legend-bar">
                <div class="lg-i"><div class="lg-dot" style="background:#10b981"></div>Depart</div>
                <div class="lg-i"><div class="lg-dot" style="background:#3b82f6"></div>Arrive</div>
                <div class="lg-i"><div class="lg-dot" style="background:#06b6d4"></div>Charging</div>
                <div class="lg-i"><div class="lg-dot" style="background:#f97316"></div>Queue Wait</div>
                <div class="lg-i"><div class="lg-dot" style="background:#475569"></div>Passed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Timeline
        tl = '<div class="tl">'
        for ev in bus_s["events"]:
            t = ev["type"]
            loc = ev.get("location", "")
            ts = ev.get("time", "")

            if t == "depart":
                tl += f'<div class="tl-ev ev-depart"><div class="tl-title">🟢 Departed {loc} at {ts}</div><div class="tl-desc">Range: {ev.get("range_km")} km</div></div>'
            elif t == "arrive":
                tl += f'<div class="tl-ev ev-arrive"><div class="tl-title">🔵 Arrived at {loc} at {ts}</div><div class="tl-desc">Remaining range: {ev.get("range_km")} km</div></div>'
            elif t == "queue_wait" and ev.get("wait_minutes", 0) > 0:
                tl += f'<div class="tl-ev ev-wait"><div class="tl-title">🟠 Queued — Waited {ev["wait_minutes"]} min</div><div class="tl-desc">Charger occupied, bus waited in queue at {loc}</div></div>'
            elif t == "charge_start":
                tl += f'<div class="tl-ev ev-charge"><div class="tl-title">🔋 Started Charging at {ts}</div><div class="tl-desc">Station {loc} — 25 min full charge</div></div>'
            elif t == "charge_end":
                tl += f'<div class="tl-ev ev-charge"><div class="tl-title">✅ Finished Charging at {ts}</div><div class="tl-desc">Battery restored to {ev.get("range_km")} km</div></div>'
            elif t == "pass":
                tl += f'<div class="tl-ev ev-pass"><div class="tl-title">⏭️ Passed {loc} at {ts}</div><div class="tl-desc">Range: {ev.get("range_km")} km — bypassed</div></div>'
        tl += "</div>"
        st.markdown(tl, unsafe_allow_html=True)
    else:
        st.info("No buses to display. Adjust filters above.")


# ═══════════ TAB 2 — PER-STATION QUEUES ═══════════
with tab2:
    st.markdown("### 🚉 Charging Station Activity")
    st.markdown("For each station (A, B, C, D), see which buses charged there, in what order, and whether they had to wait for a charger.")
    st.markdown("")

    station_items = list(route.stations.items())
    c1, c2 = st.columns(2, gap="large")

    for idx, (sid, stn) in enumerate(station_items):
        col = c1 if idx % 2 == 0 else c2
        with col:
            tw = sum(ev["wait_minutes"] for ev in stn.committed_events)
            buses_with_wait = sum(1 for ev in stn.committed_events if ev["wait_minutes"] > 0)

            card = f"""
            <div class="stn-card">
                <div class="stn-top">
                    <div class="stn-icon">{sid}</div>
                    <div>
                        <h3 style="margin:0; color:#e2e8f0; font-size:1.4rem;">{stn.name}</h3>
                        <div style="color:#64748b; font-size:0.9rem;">{stn.chargers} charger · {stn.charging_time_minutes} min per charge</div>
                    </div>
                </div>
                <div class="stn-stats">
                    <div><div class="stn-stat-label">Buses Served</div><div class="stn-stat-val purple">{len(stn.committed_events)}</div></div>
                    <div><div class="stn-stat-label">Total Wait</div><div class="stn-stat-val teal">{tw} min</div></div>
                    <div><div class="stn-stat-label">Buses Queued</div><div class="stn-stat-val amber">{buses_with_wait}</div></div>
                </div>
            """

            if stn.committed_events:
                for i, ev in enumerate(stn.committed_events):
                    badge = op_badge(ev["operator"])
                    wait_s = f'<span class="qi-wait">⏳ Waited {ev["wait_minutes"]} min</span>' if ev["wait_minutes"] > 0 else '<span class="qi-ok">✓ No Wait</span>'
                    card += f"""
                    <div class="qi">
                        <div>
                            <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.25rem;">
                                <span style="color:#64748b; font-weight:700; font-size:0.8rem;">#{i+1}</span>
                                <span class="qi-bus">{ev['bus_id']}</span>
                                {badge}
                            </div>
                            <div class="qi-time">Arr <b>{minutes_to_time(ev['arrival_time'])}</b> · Charge <b>{minutes_to_time(ev['charge_start'])}</b> → <b>{minutes_to_time(ev['charge_end'])}</b></div>
                        </div>
                        <div>{wait_s}</div>
                    </div>"""
            else:
                card += '<p style="color:#475569; text-align:center; padding:2rem 0; font-style:italic;">No buses charged here</p>'

            card += "</div>"
            st.markdown(card, unsafe_allow_html=True)


# ═══════════ TAB 3 — SCENARIO INPUTS ═══════════
with tab3:
    st.markdown("### 📁 Scenario Input Data")
    st.markdown("The raw data being fed into the scheduler for this scenario — network structure, physical parameters, weights, and bus fleet departures.")
    st.markdown("")

    c_left, c_right = st.columns(2, gap="large")

    with c_left:
        st.markdown("#### 🌐 Network, Parameters & Weights")
        st.json({
            "name": scenario_data["name"],
            "description": scenario_data["description"],
            "network": {
                "endpoints": scenario_data["network"]["endpoints"],
                "stations": scenario_data["network"]["stations"],
                "segments": scenario_data["network"]["segments"],
            },
            "parameters": scenario_data["parameters"],
            "weights": scenario_data["weights"],
        })

    with c_right:
        st.markdown("#### 🚌 Fleet Departure Timetable")
        bus_input_rows = [
            {"Bus ID": b["id"], "Operator": b["operator"], "Direction": b["direction"], "Departure": b["departure"]}
            for b in scenario_data["buses"]
        ]
        st.dataframe(
            pd.DataFrame(bus_input_rows),
            use_container_width=True,
            hide_index=True,
            height=min(len(bus_input_rows) * 42 + 60, 700),
        )
