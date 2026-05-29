import streamlit as st
import json
import os
import pandas as pd
from typing import Dict, Any, List

from scheduler.models import Route, Station, Segment, Bus, time_to_minutes
from scheduler.engine import SchedulerEngine

# -------------------------------------------------------------
# Page Configuration & Modern Glassmorphism Styling
# -------------------------------------------------------------
st.set_page_config(
    page_title="VoltTransit — Bidirectional Bus Charging Scheduler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling injection
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">
    
    <style>
    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Header Gradient */
    .header-container {
        background: linear-gradient(135deg, #1e1b4b 0%, #311042 50%, #030712 100%);
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    .header-title {
        background: linear-gradient(90deg, #a78bfa 0%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
    }
    .header-subtitle {
        color: #9ca3af;
        font-size: 1.1rem;
        font-weight: 400;
        margin-top: 0.5rem;
    }
    
    /* Premium KPI Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    .kpi-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        border-color: rgba(56, 189, 248, 0.3);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        color: #38bdf8;
        font-family: 'Outfit', sans-serif;
        margin-bottom: 0.25rem;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Sleek Badges for Operators */
    .badge {
        padding: 0.25rem 0.6rem;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
        letter-spacing: 0.5px;
    }
    .badge-kpn { background-color: rgba(167, 139, 250, 0.15); color: #c084fc; border: 1px solid rgba(167, 139, 250, 0.3); }
    .badge-freshbus { background-color: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }
    .badge-flixbus { background-color: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.3); }
    
    /* Event Timeline Styles */
    .timeline-item {
        border-left: 2px solid rgba(255, 255, 255, 0.1);
        padding-left: 20px;
        position: relative;
        padding-bottom: 1.5rem;
    }
    .timeline-item::before {
        content: '';
        width: 12px;
        height: 12px;
        border-radius: 50%;
        position: absolute;
        left: -7px;
        top: 4px;
        background-color: #4b5563;
    }
    
    /* Timeline Node Variants */
    .timeline-depart::before { background-color: #10b981; box-shadow: 0 0 8px #10b981; }
    .timeline-arrive::before { background-color: #3b82f6; box-shadow: 0 0 8px #3b82f6; }
    .timeline-wait::before { background-color: #f97316; box-shadow: 0 0 8px #f97316; }
    .timeline-charge::before { background-color: #06b6d4; box-shadow: 0 0 8px #06b6d4; }
    .timeline-pass::before { background-color: #6b7280; }
    
    .timeline-title {
        font-weight: 700;
        color: #f3f4f6;
        font-size: 0.95rem;
    }
    .timeline-desc {
        font-size: 0.85rem;
        color: #9ca3af;
        margin-top: 0.2rem;
    }
    
    /* Sidebar styling enhancements */
    .sidebar-card {
        background: rgba(30, 41, 59, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------------------
# Core Load & Compute Functions
# -------------------------------------------------------------
SCENARIOS_DIR = "scenarios"

@st.cache_data
def list_available_scenarios() -> List[str]:
    """List all scenario configuration files sorted."""
    if not os.path.exists(SCENARIOS_DIR):
        return []
    files = [f for f in os.listdir(SCENARIOS_DIR) if f.endswith(".json")]
    return sorted(files)

def load_scenario(filename: str) -> Dict[str, Any]:
    """Load scenario data from JSON file."""
    filepath = os.path.join(SCENARIOS_DIR, filename)
    with open(filepath, "r") as f:
        return json.load(f)

# -------------------------------------------------------------
# Header Layout
# -------------------------------------------------------------
st.markdown(
    """
    <div class="header-container">
        <h1 class="header-title">⚡ VoltTransit</h1>
        <div class="header-subtitle">Advanced Electric Fleet Simulation & Bidirectional Charging Scheduler</div>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------------------
# Sidebar Configuration
# -------------------------------------------------------------
st.sidebar.markdown("### 🛠️ Configuration")

# Scenario Selection
scenarios = list_available_scenarios()
if not scenarios:
    st.sidebar.error("No scenario configuration files found in 'scenarios/' directory.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Select Simulation Scenario",
    scenarios,
    format_func=lambda x: x.replace(".json", "").replace("_", " ").title()
)

scenario_data = load_scenario(selected_file)

# Load weight configurations
default_weights = scenario_data.get("weights", {"individual": 1.0, "operator": 1.0, "overall": 1.0})

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Optimization Weights")
st.sidebar.caption("Fine-tune weights below to dynamically trigger live schedule re-simulations.")

# Tunable Sliders
w_individual = st.sidebar.slider(
    "Individual Bus Wait Time",
    min_value=0.0,
    max_value=5.0,
    value=float(default_weights.get("individual", 1.0)),
    step=0.1,
    help="Higher weight penalizes queue wait times for individual buses. Steers buses away from congested stations."
)

w_operator = st.sidebar.slider(
    "Operator Fleet Coordination",
    min_value=0.0,
    max_value=5.0,
    value=float(default_weights.get("operator", 1.0)),
    step=0.1,
    help="Higher weight keeps same-operator buses' total trip times cohesive as a group."
)

w_overall = st.sidebar.slider(
    "Overall Network Time",
    min_value=0.0,
    max_value=5.0,
    value=float(default_weights.get("overall", 1.0)),
    step=0.1,
    help="Higher weight minimizes each bus's total travel time, preferring fewer charging stops."
)

# Sidebar Parameters Card
st.sidebar.markdown("---")
st.sidebar.markdown("### 📐 Physical Parameters")

params = scenario_data.get("parameters", {"bus_speed_kmh": 60, "max_range_km": 240})
bus_speed = params.get("bus_speed_kmh", 60)
max_range = params.get("max_range_km", 240)

st.sidebar.markdown(
    f"""
    <div class="sidebar-card">
        <p style="margin: 0; font-size: 0.85rem; color: #9ca3af;">Uniform Travel Speed</p>
        <h4 style="margin: 0 0 0.5rem 0; color: #38bdf8; font-size: 1.25rem;">{bus_speed} km/h</h4>
        <p style="margin: 0; font-size: 0.85rem; color: #9ca3af;">Maximum Battery Range</p>
        <h4 style="margin: 0; color: #38bdf8; font-size: 1.25rem;">{max_range} km</h4>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------------------
# Simulation Run Execution
# -------------------------------------------------------------
# Reconstruct Route
network = scenario_data["network"]
endpoints = network["endpoints"]
stations = [
    Station(s["id"], s["name"], s["chargers"], s["charging_time_minutes"])
    for s in network["stations"]
]
segments = [
    Segment(seg["from"], seg["to"], seg["distance_km"])
    for seg in network["segments"]
]
route = Route(endpoints, stations, segments)

# Reconstruct Buses
buses = [
    Bus(b["id"], b["operator"], b["direction"], b["departure"])
    for b in scenario_data["buses"]
]

# Run Simulation Engine
weights_override = {
    "individual": w_individual,
    "operator": w_operator,
    "overall": w_overall
}

engine = SchedulerEngine(route, params, weights_override)
schedules = engine.schedule_all(buses)

# -------------------------------------------------------------
# Main Application Content & Tabs
# -------------------------------------------------------------
st.subheader(f"📊 {scenario_data['name']}")
st.write(f"*{scenario_data['description']}*")

# Compute overall metrics
total_buses = len(schedules)
total_wait = sum(s["total_wait_minutes"] for s in schedules)
avg_wait = total_wait / total_buses if total_buses > 0 else 0
max_wait = max(s["total_wait_minutes"] for s in schedules) if total_buses > 0 else 0
total_trip = sum(s["total_trip_minutes"] for s in schedules)
avg_trip = total_trip / total_buses if total_buses > 0 else 0

st.markdown(
    f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-value">{total_buses}</div>
            <div class="kpi-label">Buses Scheduled</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{avg_wait:.1f} m</div>
            <div class="kpi-label">Avg Queue Wait</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{max_wait} m</div>
            <div class="kpi-label">Max Queue Wait</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{avg_trip:.1f} m</div>
            <div class="kpi-label">Avg Trip Time</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

tab1, tab2, tab3 = st.tabs(["🕒 Per-Bus Timetable", "🚉 Per-Station Queues", "📁 Scenario Inputs"])

# Operator badge renderer helper
def get_operator_badge(op: str) -> str:
    op_lower = op.lower()
    if "kpn" in op_lower:
        return f'<span class="badge badge-kpn">{op}</span>'
    elif "fresh" in op_lower:
        return f'<span class="badge badge-freshbus">{op}</span>'
    else:
        return f'<span class="badge badge-flixbus">{op}</span>'

# TAB 1: Per-Bus Timetable
with tab1:
    col_filters, col_table = st.columns([1, 3])
    
    with col_filters:
        st.markdown("##### 🔍 Search & Filter")
        search_bus = st.text_input("Search Bus ID (e.g. BK-01)", "").strip().upper()
        
        operators = sorted(list(set(s["operator"] for s in schedules)))
        selected_op = st.multiselect("Filter Operator", operators, default=operators)
        
        directions = sorted(list(set(s["direction"] for s in schedules)))
        selected_dir = st.multiselect("Filter Direction", directions, default=directions)
        
        # Interactive click to view detail in timeline
        filtered_schedules = [
            s for s in schedules
            if (search_bus in s["bus_id"].upper())
            and (s["operator"] in selected_op)
            and (s["direction"] in selected_dir)
        ]
        
        bus_list = [s["bus_id"] for s in filtered_schedules]
        if bus_list:
            selected_bus_id = st.selectbox("Select Bus to View Event Path", bus_list)
        else:
            selected_bus_id = None
            
    with col_table:
        st.markdown("##### 🕒 Schedules Summary")
        
        summary_rows = []
        for s in filtered_schedules:
            summary_rows.append({
                "Bus ID": s["bus_id"],
                "Operator": s["operator"],
                "Direction": s["direction"],
                "Departure": s["departure_time"],
                "Arrival": s["arrival_time"],
                "Trip Duration": f"{s['total_trip_minutes']} min",
                "Wait Time": f"{s['total_wait_minutes']} min",
                "Stops": ", ".join(s["charging_plan"]) if s["charging_plan"] else "None"
            })
            
        if summary_rows:
            df = pd.DataFrame(summary_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No buses match the chosen filters.")
            
    if selected_bus_id:
        st.markdown("---")
        st.markdown(f"#### 🗺️ Journey Path & Charging Log: **{selected_bus_id}**")
        
        bus_sched = next(s for s in schedules if s["bus_id"] == selected_bus_id)
        
        # Build timeline UI
        st.write(f"Direction: **{bus_sched['direction']}** | Operator: **{bus_sched['operator']}**")
        
        timeline_html = '<div style="margin-top: 1rem; margin-bottom: 2rem;">'
        
        for ev in bus_sched["events"]:
            ev_type = ev["type"]
            loc = ev["location"]
            time_str = ev.get("time", "")
            
            if ev_type == "depart":
                timeline_html += f"""
                <div class="timeline-item timeline-depart">
                    <div class="timeline-title">Departed {loc} at {time_str}</div>
                    <div class="timeline-desc">Initial range: {ev.get('range_km')} km</div>
                </div>
                """
            elif ev_type == "arrive":
                timeline_html += f"""
                <div class="timeline-item timeline-arrive">
                    <div class="timeline-title">Arrived at {loc} at {time_str}</div>
                    <div class="timeline-desc">Remaining battery range: {ev.get('range_km')} km</div>
                </div>
                """
            elif ev_type == "queue_wait":
                wait_min = ev.get("wait_minutes", 0)
                if wait_min > 0:
                    timeline_html += f"""
                    <div class="timeline-item timeline-wait">
                        <div class="timeline-title" style="color: #f97316;">Queued in Contention: Waited {wait_min} min</div>
                        <div class="timeline-desc">Station charging resources fully occupied.</div>
                    </div>
                    """
            elif ev_type == "charge_start":
                timeline_html += f"""
                <div class="timeline-item timeline-charge">
                    <div class="timeline-title">Started Charging at {time_str}</div>
                </div>
                """
            elif ev_type == "charge_end":
                timeline_html += f"""
                <div class="timeline-item timeline-charge">
                    <div class="timeline-title">Finished Charging at {time_str}</div>
                    <div class="timeline-desc">Battery range fully restored to {ev.get('range_km')} km</div>
                </div>
                """
            elif ev_type == "pass":
                timeline_html += f"""
                <div class="timeline-item timeline-pass">
                    <div class="timeline-title">Passed Station {loc} at {time_str}</div>
                    <div class="timeline-desc">Remaining range: {ev.get('range_km')} km (bypassed charging)</div>
                </div>
                """
                
        timeline_html += '</div>'
        st.markdown(timeline_html, unsafe_allow_html=True)

# TAB 2: Per-Station Queues
with tab2:
    st.markdown("##### 🚉 Charging Stations Activity Logs")
    st.caption("Inspect the exact charging sequence, queue waits, and charger occupancy at each intermediate station.")
    
    cols = st.columns(len(route.stations))
    
    for idx, (station_id, station) in enumerate(route.stations.items()):
        with cols[idx]:
            st.markdown(f"### Station {station_id}")
            st.markdown(
                f"""
                <div style="background: rgba(30, 41, 59, 0.3); border-radius: 12px; padding: 1rem; border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 1rem;">
                    <div style="font-size: 0.8rem; color: #9ca3af; text-transform: uppercase;">Shared Chargers</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #38bdf8;">{station.chargers}</div>
                    <div style="font-size: 0.8rem; color: #9ca3af; text-transform: uppercase; margin-top: 0.5rem;">Buses Served</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #a78bfa;">{len(station.committed_events)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            if station.committed_events:
                # Render sequential list
                log_html = '<div style="display: flex; flex-direction: column; gap: 0.75rem;">'
                for ev in station.committed_events:
                    op_badge = get_operator_badge(ev['operator'])
                    wait_str = f"<span style='color:#f97316; font-weight:bold;'>Waited {ev['wait_minutes']}m</span>" if ev['wait_minutes'] > 0 else "<span style='color:#10b981;'>No Wait</span>"
                    
                    log_html += f"""
                    <div style="background: rgba(15, 23, 42, 0.4); padding: 0.85rem; border-radius: 10px; border: 1px solid rgba(255,255,255,0.03);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                            <span style="font-weight: 700; color: #f3f4f6; font-size: 0.9rem;">{ev['bus_id']}</span>
                            {op_badge}
                        </div>
                        <div style="font-size: 0.75rem; color: #9ca3af;">
                            Arr: <b>{minutes_to_time(ev['arrival_time'])}</b> | Charge: <b>{minutes_to_time(ev['charge_start'])} - {minutes_to_time(ev['charge_end'])}</b>
                        </div>
                        <div style="font-size: 0.75rem; margin-top: 0.2rem;">
                            Status: {wait_str}
                        </div>
                    </div>
                    """
                log_html += '</div>'
                st.markdown(log_html, unsafe_allow_html=True)
            else:
                st.info("No buses charged at this station.")

# TAB 3: Scenario Inputs
with tab3:
    st.markdown("##### 📁 Scenario Configuration JSON Structure & Raw Schedule")
    
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.markdown("**1. Physical Parameters & Weight Offsets**")
        st.json({
            "name": scenario_data["name"],
            "description": scenario_data["description"],
            "network": {
                "endpoints": scenario_data["network"]["endpoints"],
                "stations": scenario_data["network"]["stations"],
                "segments": scenario_data["network"]["segments"]
            },
            "parameters": scenario_data["parameters"],
            "weights": scenario_data["weights"]
        })
        
    with col_r:
        st.markdown("**2. Fleet Departure Timetable**")
        input_buses_rows = [
            {
                "Bus ID": b["id"],
                "Operator": b["operator"],
                "Direction": b["direction"],
                "Departure Time": b["departure"]
            }
            for b in scenario_data["buses"]
        ]
        st.dataframe(pd.DataFrame(input_buses_rows), use_container_width=True, hide_index=True)
