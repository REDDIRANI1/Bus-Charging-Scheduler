import json
from scheduler.models import Route, Station
from scheduler.engine import SchedulerEngine
from scheduler.utils import load_scenario

def test_all():
    route = Route()
    route.add_station(Station("A", chargers=1))
    route.add_station(Station("B", chargers=1))
    route.add_station(Station("C", chargers=1))
    route.add_station(Station("D", chargers=1))
    
    scenarios = [
        ("Scenario 1", "data/scenario_1.json", {"individual": 1.0, "operator": 1.0, "overall": 1.0}),
        ("Scenario 2", "data/scenario_2.json", {"individual": 1.0, "operator": 1.0, "overall": 1.0}),
        ("Scenario 3", "data/scenario_3.json", {"individual": 1.0, "operator": 1.0, "overall": 1.0}),
        ("Scenario 4", "data/scenario_4.json", {"individual": 1.0, "operator": 2.0, "overall": 1.0}),
        ("Scenario 5", "data/scenario_5.json", {"individual": 1.0, "operator": 1.0, "overall": 1.0}),
    ]
    
    for name, path, weights in scenarios:
        print(f"Testing {name}...")
        route.reset() # clear station events
        buses = load_scenario(path)
        engine = SchedulerEngine(route, {}, weights)
        schedules = engine.schedule_all(buses)
        print(f"  {name} successfully scheduled {len(schedules)} buses.")
        # Verify 240km range limit logic hasn't failed for any bus
        for sched in schedules:
            assert len(sched['charging_plan']) >= 2, f"Bus {sched['bus_id']} didn't charge at least twice!"

if __name__ == "__main__":
    test_all()
