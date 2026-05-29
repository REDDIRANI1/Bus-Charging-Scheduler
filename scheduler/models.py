from typing import List, Dict, Any

def time_to_minutes(time_str: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m

def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM (24-hour format wrapping past midnight)."""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

class Station:
    def __init__(self, station_id: str, name: str, chargers: int, charging_time_minutes: int):
        self.id = station_id
        self.name = name
        self.chargers = chargers
        self.charging_time_minutes = charging_time_minutes
        # List of committed charging events: each is a dict with:
        # {'bus_id': str, 'operator': str, 'arrival_time': int, 'charge_start': int, 'charge_end': int, 'wait_minutes': int}
        self.committed_events = []

    def add_event(self, event: Dict[str, Any]):
        self.committed_events.append(event)
        # Keep events sorted by charge_start to make queue log clean
        self.committed_events.sort(key=lambda x: x['charge_start'])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.id,
            "chargers": self.chargers,
            "total_buses_served": len(self.committed_events),
            "queue": [
                {
                    "bus_id": ev["bus_id"],
                    "operator": ev["operator"],
                    "arrival_time": minutes_to_time(ev["arrival_time"]),
                    "charge_start": minutes_to_time(ev["charge_start"]),
                    "charge_end": minutes_to_time(ev["charge_end"]),
                    "wait_minutes": ev["wait_minutes"]
                }
                for ev in self.committed_events
            ]
        }

class Segment:
    def __init__(self, from_node: str, to_node: str, distance_km: float):
        self.from_node = from_node
        self.to_node = to_node
        self.distance_km = distance_km

class Route:
    def __init__(self, endpoints: List[str], stations: List[Station], segments: List[Segment]):
        self.endpoints = endpoints
        self.stations = {s.id: s for s in stations}
        self.segments = segments
        
        # Build adjacency or list of nodes in standard order
        # We assume standard order is endpoints[0] -> stations in order -> endpoints[1]
        # Let's determine standard sequence by traversing segments from endpoints[0]
        self.nodes_sequence = self._derive_nodes_sequence()

    def _derive_nodes_sequence(self) -> List[str]:
        # To be robust, let's trace the segments from endpoints[0] to endpoints[1]
        start = self.endpoints[0]
        end = self.endpoints[1]
        
        seq = [start]
        curr = start
        visited = {start}
        
        while curr != end:
            next_node = None
            for seg in self.segments:
                if seg.from_node == curr and seg.to_node not in visited:
                    next_node = seg.to_node
                    break
                elif seg.to_node == curr and seg.from_node not in visited:
                    next_node = seg.from_node
                    break
            if not next_node:
                # Fallback: if segments are not perfectly chained, just return endpoints + stations
                return [start] + list(self.stations.keys()) + [end]
            seq.append(next_node)
            visited.add(next_node)
            curr = next_node
        return seq

    def get_nodes_in_direction(self, direction: str) -> List[str]:
        """Return the sequence of nodes for a given direction."""
        # direction is like "Bengaluru→Kochi" or "Kochi→Bengaluru"
        # We split by '→' or '->' to see starting and ending endpoints
        sep = '→' if '→' in direction else '->'
        parts = direction.split(sep)
        start_ep = parts[0].strip()
        
        if start_ep == self.endpoints[0]:
            return self.nodes_sequence
        else:
            return list(reversed(self.nodes_sequence))

    def get_distance(self, from_node: str, to_node: str) -> float:
        """Get distance between two adjacent or non-adjacent nodes along the sequence."""
        # Find their positions in the sequence
        try:
            i1 = self.nodes_sequence.index(from_node)
            i2 = self.nodes_sequence.index(to_node)
        except ValueError:
            raise ValueError(f"Nodes {from_node} or {to_node} not found in route sequence.")
            
        start_idx, end_idx = min(i1, i2), max(i1, i2)
        
        # Sum distances of segments between consecutive nodes in the sequence
        total_dist = 0.0
        for i in range(start_idx, end_idx):
            n1 = self.nodes_sequence[i]
            n2 = self.nodes_sequence[i+1]
            # Find segment matching n1-n2
            found = False
            for seg in self.segments:
                if (seg.from_node == n1 and seg.to_node == n2) or (seg.from_node == n2 and seg.to_node == n1):
                    total_dist += seg.distance_km
                    found = True
                    break
            if not found:
                raise ValueError(f"No segment found between consecutive nodes {n1} and {n2} in route sequence.")
        return total_dist

class Bus:
    def __init__(self, bus_id: str, operator: str, direction: str, departure_str: str):
        self.id = bus_id
        self.operator = operator
        self.direction = direction
        self.departure_str = departure_str
        self.departure_minutes = time_to_minutes(departure_str)
