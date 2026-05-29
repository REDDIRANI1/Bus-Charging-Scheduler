from typing import List, Dict, Any, Tuple
import itertools
from scheduler.models import Route, Bus, Station, minutes_to_time
from scheduler.constraints import RangeConstraint, SequenceConstraint
from scheduler.scorers import IndividualWaitScorer, OperatorFleetScorer, OverallNetworkTimeScorer

def is_available(S: int, duration: int, committed_events: List[Dict[str, Any]], chargers: int) -> bool:
    """Check if a charger is available for the entire interval [S, S + duration]."""
    points = [S]
    for ev in committed_events:
        if S < ev["charge_start"] < S + duration:
            points.append(ev["charge_start"])
        if S < ev["charge_end"] < S + duration:
            points.append(ev["charge_end"])
            
    points = sorted(list(set(points)))
    
    for p in points:
        active_count = sum(1 for ev in committed_events if ev["charge_start"] <= p < ev["charge_end"])
        if active_count >= chargers:
            return False
    return True

def find_earliest_charge_start(arrival_time: int, duration: int, committed_events: List[Dict[str, Any]], chargers: int) -> int:
    """Find the earliest start time >= arrival_time where a charger is available for duration."""
    candidates = [arrival_time]
    for ev in committed_events:
        if ev["charge_end"] > arrival_time:
            candidates.append(ev["charge_end"])
    candidates = sorted(list(set(candidates)))
    
    for S in candidates:
        if is_available(S, duration, committed_events, chargers):
            return S
    return arrival_time

def simulate_trip(plan: List[str], bus: Bus, route: Route, bus_speed_kmh: float, max_range_km: float, charging_time_minutes: int) -> Dict[str, Any]:
    """Simulate a candidate charging plan for a bus without modifying the committed state."""
    nodes_seq = route.get_nodes_in_direction(bus.direction)
    origin = nodes_seq[0]
    destination = nodes_seq[-1]
    
    current_time = bus.departure_minutes
    current_range = max_range_km
    
    events = [
        {
            "type": "depart",
            "location": origin,
            "time": minutes_to_time(current_time),
            "time_minutes": current_time,
            "range_km": int(current_range)
        }
    ]
    
    total_wait_minutes = 0
    prev_node = origin
    
    for curr_node in nodes_seq[1:]:
        dist = route.get_distance(prev_node, curr_node)
        travel_time_min = int(round((dist / bus_speed_kmh) * 60))
        current_range -= dist
        current_time += travel_time_min
        
        # Check range constraint (fail-safe, should be caught by hard constraints, but let's be safe)
        if current_range < 0:
            raise ValueError(f"Range dropped below 0 to {current_range} km while traveling to {curr_node}")
            
        if curr_node == destination:
            events.append({
                "type": "arrive",
                "location": curr_node,
                "time": minutes_to_time(current_time),
                "time_minutes": current_time,
                "range_km": int(current_range)
            })
        else:
            # Intermediate station
            if curr_node in plan:
                station = route.stations[curr_node]
                # Simulate arrival
                arr_time = current_time
                arr_range = current_range
                events.append({
                    "type": "arrive",
                    "location": curr_node,
                    "time": minutes_to_time(arr_time),
                    "time_minutes": arr_time,
                    "range_km": int(arr_range)
                })
                
                # Find charge start with queuing simulation
                charge_start = find_earliest_charge_start(arr_time, charging_time_minutes, station.committed_events, station.chargers)
                wait = charge_start - arr_time
                total_wait_minutes += wait
                charge_end = charge_start + charging_time_minutes
                
                events.append({
                    "type": "queue_wait",
                    "location": curr_node,
                    "wait_minutes": wait
                })
                events.append({
                    "type": "charge_start",
                    "location": curr_node,
                    "time": minutes_to_time(charge_start),
                    "time_minutes": charge_start
                })
                events.append({
                    "type": "charge_end",
                    "location": curr_node,
                    "time": minutes_to_time(charge_end),
                    "time_minutes": charge_end,
                    "range_km": int(max_range_km)
                })
                events.append({
                    "type": "depart",
                    "location": curr_node,
                    "time": minutes_to_time(charge_end),
                    "time_minutes": charge_end,
                    "range_km": int(max_range_km)
                })
                
                current_time = charge_end
                current_range = max_range_km
            else:
                # Just passing by
                events.append({
                    "type": "pass",
                    "location": curr_node,
                    "time": minutes_to_time(current_time),
                    "time_minutes": current_time,
                    "range_km": int(current_range)
                })
                
        prev_node = curr_node
        
    return {
        "bus_id": bus.id,
        "operator": bus.operator,
        "direction": bus.direction,
        "departure_time": bus.departure_str,
        "arrival_time": minutes_to_time(current_time),
        "total_trip_minutes": current_time - bus.departure_minutes,
        "total_wait_minutes": total_wait_minutes,
        "charging_plan": plan,
        "events": events
    }

class SchedulerEngine:
    def __init__(self, route: Route, parameters: Dict[str, Any], weights: Dict[str, float]):
        self.route = route
        self.bus_speed_kmh = parameters.get("bus_speed_kmh", 60.0)
        self.max_range_km = parameters.get("max_range_km", 240.0)
        self.charging_time_minutes = parameters.get("charging_time_minutes", 25)
        self.weights = weights
        
        # Pluggable hard constraints
        self.hard_constraints = [
            RangeConstraint(),
            SequenceConstraint()
        ]
        
        # Pluggable soft scorers
        self.soft_scorers = [
            (IndividualWaitScorer(), self.weights.get("individual", 1.0)),
            (OperatorFleetScorer(), self.weights.get("operator", 1.0)),
            (OverallNetworkTimeScorer(), self.weights.get("overall", 1.0))
        ]
        
        self.committed_schedules = []

    def get_feasible_plans(self, bus: Bus) -> List[List[str]]:
        """Generate all feasible charging plans that satisfy the hard constraints."""
        # Get stations in the order of travel
        nodes_seq = self.route.get_nodes_in_direction(bus.direction)
        stations_seq = [node for node in nodes_seq if node in self.route.stations]
        
        feasible_plans = []
        
        # Generate all subsets of stations of any size
        for r in range(len(stations_seq) + 1):
            for subset in itertools.combinations(stations_seq, r):
                plan = list(subset)
                
                # Check if it satisfies all hard constraints
                valid = True
                for constraint in self.hard_constraints:
                    if not constraint.is_valid(plan, bus, self.route, self.max_range_km):
                        valid = False
                        break
                
                if valid:
                    feasible_plans.append(plan)
                    
        return feasible_plans

    def schedule_bus(self, bus: Bus) -> Dict[str, Any]:
        """Find the best plan for a bus, commit it, and return its schedule."""
        plans = self.get_feasible_plans(bus)
        
        if not plans:
            raise ValueError(f"No feasible charging plan found for bus {bus.id} given physical constraints.")
            
        best_plan = None
        best_score = float('inf')
        best_trip = None
        
        # Evaluate each plan
        for plan in plans:
            # Simulate the trip against the currently committed state
            sim_trip = simulate_trip(
                plan, bus, self.route, 
                self.bus_speed_kmh, self.max_range_km, 
                self.charging_time_minutes
            )
            
            # Compute composite cost using soft scorers
            composite_cost = 0.0
            for scorer, weight in self.soft_scorers:
                score_val = scorer.score(plan, bus, self.route, sim_trip, self.committed_schedules)
                composite_cost += weight * score_val
                
            if composite_cost < best_score:
                best_score = composite_cost
                best_plan = plan
                best_trip = sim_trip
                
        # Commit the best plan by adding the events to the stations
        # We need to run simulation again to get exact event timings and add to station queue state
        final_trip = best_trip
        
        # Record the events in the station committed logs
        # To match exact timing, we find each charging event in the final_trip events list
        for i, ev in enumerate(final_trip["events"]):
            if ev["type"] == "charge_start":
                station_id = ev["location"]
                start_min = ev["time_minutes"]
                
                # Find matching charge_end
                end_min = None
                for ev_next in final_trip["events"][i+1:]:
                    if ev_next["type"] == "charge_end" and ev_next["location"] == station_id:
                        end_min = ev_next["time_minutes"]
                        break
                
                # Find matching queue_wait
                wait_minutes = 0
                for ev_prev in reversed(final_trip["events"][:i]):
                    if ev_prev["type"] == "queue_wait" and ev_prev["location"] == station_id:
                        wait_minutes = ev_prev["wait_minutes"]
                        break
                
                # Find arrival_time
                arrival_min = None
                for ev_prev in reversed(final_trip["events"][:i]):
                    if ev_prev["type"] == "arrive" and ev_prev["location"] == station_id:
                        arrival_min = ev_prev["time_minutes"]
                        break
                
                station = self.route.stations[station_id]
                station.add_event({
                    "bus_id": bus.id,
                    "operator": bus.operator,
                    "arrival_time": arrival_min,
                    "charge_start": start_min,
                    "charge_end": end_min,
                    "wait_minutes": wait_minutes
                })
                
        self.committed_schedules.append(final_trip)
        return final_trip

    def schedule_all(self, buses: List[Bus]) -> List[Dict[str, Any]]:
        """Sort buses by departure time, schedule them one by one, and return all schedules."""
        sorted_buses = sorted(buses, key=lambda b: b.departure_minutes)
        schedules = []
        for bus in sorted_buses:
            schedules.append(self.schedule_bus(bus))
        return schedules
