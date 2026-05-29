import json
import os
import unittest
from scheduler.models import Route, Station, Segment, Bus, time_to_minutes
from scheduler.engine import SchedulerEngine

class TestBusChargingScheduler(unittest.TestCase):
    def setUp(self):
        # Find scenario 1 path
        self.scenario_path = "scenarios/scenario_1.json"
        with open(self.scenario_path, "r") as f:
            self.scenario_data = json.load(f)
            
        # Parse Route
        network = self.scenario_data["network"]
        endpoints = network["endpoints"]
        stations = [
            Station(s["id"], s["name"], s["chargers"], s["charging_time_minutes"])
            for s in network["stations"]
        ]
        segments = [
            Segment(seg["from"], seg["to"], seg["distance_km"])
            for seg in network["segments"]
        ]
        self.route = Route(endpoints, stations, segments)
        
        # Parse Buses
        self.buses = [
            Bus(b["id"], b["operator"], b["direction"], b["departure"])
            for b in self.scenario_data["buses"]
        ]
        
        # Parse params
        self.params = self.scenario_data["parameters"]
        self.weights = self.scenario_data["weights"]

    def test_scheduling_correctness(self):
        for s_idx in range(1, 6):
            scenario_path = f"scenarios/scenario_{s_idx}.json"
            with open(scenario_path, "r") as f:
                scenario_data = json.load(f)
                
            # Parse Route
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
            
            # Parse Buses
            buses = [
                Bus(b["id"], b["operator"], b["direction"], b["departure"])
                for b in scenario_data["buses"]
            ]
            
            # Parse params
            params = scenario_data["parameters"]
            weights = scenario_data["weights"]
            
            engine = SchedulerEngine(route, params, weights)
            schedules = engine.schedule_all(buses)
            
            self.assertEqual(len(schedules), len(buses), f"Scenario {s_idx} failed: bus count mismatch.")
            
            max_range = params["max_range_km"]
            charging_duration = params.get("charging_time_minutes", 25)
            
            for sched in schedules:
                bus_id = sched["bus_id"]
                direction = sched["direction"]
                events = sched["events"]
                
                # Check range never drops below 0 and that start/ends are correct
                prev_time_min = -1
                charging_stops = []
                
                day_offset = 0
                for ev in events:
                    if "time" in ev:
                        ev_time_min = time_to_minutes(ev["time"]) + day_offset
                        if ev_time_min < prev_time_min:
                            # Time wrapped around midnight!
                            ev_time_min += 1440
                            day_offset += 1440
                    else:
                        # queue_wait event might not have time, but let's keep it chronologically aligned
                        ev_time_min = prev_time_min
                    
                    if ev["type"] != "queue_wait":
                        self.assertGreaterEqual(ev_time_min, prev_time_min, f"Scenario {s_idx}, Bus {bus_id} has out-of-order event times.")
                        prev_time_min = ev_time_min
                    
                    if ev["type"] == "depart":
                        if ev["location"] == route.endpoints[0] or ev["location"] == route.endpoints[1]:
                            # Origin departure
                            self.assertEqual(ev["range_km"], max_range, f"Scenario {s_idx}, Bus {bus_id} origin depart range is incorrect.")
                        else:
                            # Station departure
                            self.assertEqual(ev["range_km"], max_range, f"Scenario {s_idx}, Bus {bus_id} station depart range is incorrect.")
                            
                    elif ev["type"] == "arrive":
                        # Range should be >= 0
                        self.assertGreaterEqual(ev["range_km"], 0, f"Scenario {s_idx}, Bus {bus_id} ran out of range arriving at {ev['location']}")
                        
                    elif ev["type"] == "pass":
                        self.assertGreaterEqual(ev["range_km"], 0, f"Scenario {s_idx}, Bus {bus_id} ran out of range passing {ev['location']}")
                        
                    elif ev["type"] == "charge_start":
                        charge_start_time = ev_time_min
                        
                    elif ev["type"] == "charge_end":
                        # Verify charging took exactly charging_duration
                        actual_duration = ev_time_min - charge_start_time
                        self.assertEqual(actual_duration, charging_duration, f"Scenario {s_idx}, Bus {bus_id} charging took {actual_duration} minutes instead of {charging_duration}")
                        self.assertEqual(ev["range_km"], max_range, f"Scenario {s_idx}, Bus {bus_id} charge end range is incorrect.")
                        charging_stops.append(ev["location"])
                
                # No backtracking: charging stops must be visited in travel order
                nodes_seq = route.get_nodes_in_direction(direction)
                station_seq = [n for n in nodes_seq if n in route.stations]
                
                last_idx = -1
                for stop in charging_stops:
                    curr_idx = station_seq.index(stop)
                    self.assertGreater(curr_idx, last_idx, f"Scenario {s_idx}, Bus {bus_id} did backtracking! Stops: {charging_stops}")
                    last_idx = curr_idx
                    
                # Minimum 2 charges on full 540 km trip
                self.assertGreaterEqual(len(charging_stops), 2, f"Scenario {s_idx}, Bus {bus_id} had only {len(charging_stops)} stops for a 540 km trip!")

            # Verify charger capacity is respected at every minute of the simulation
            # For each station, count concurrent charges
            for station_id, station in route.stations.items():
                max_chargers = station.chargers
                events_list = station.committed_events
                
                # We can check overlap of all committed events
                for i, ev1 in enumerate(events_list):
                    overlap_count = 1
                    for j, ev2 in enumerate(events_list):
                        if i == j:
                            continue
                        # Check if ev2 overlaps with ev1
                        # Two intervals [s1, e1] and [s2, e2] overlap if s1 < e2 and s2 < e1
                        if ev1["charge_start"] < ev2["charge_end"] and ev2["charge_start"] < ev1["charge_end"]:
                            overlap_count += 1
                    self.assertLessEqual(overlap_count, max_chargers, f"Scenario {s_idx}, Station {station_id} exceeded charger capacity! Concurrent charges: {overlap_count}")

if __name__ == "__main__":
    unittest.main()
