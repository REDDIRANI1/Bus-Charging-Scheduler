from abc import ABC, abstractmethod
from typing import List
from scheduler.models import Route, Bus

class HardConstraint(ABC):
    """Abstract class for pluggable hard constraints."""
    
    @abstractmethod
    def is_valid(self, plan: List[str], bus: Bus, route: Route, max_range_km: float) -> bool:
        """
        Return True if the candidate charging plan is physically valid for the bus.
        
        :param plan: List of station IDs representing the chosen charging stations (e.g., ['A', 'C'])
        :param bus: The Bus object being scheduled
        :param route: The Route object containing segments and distances
        :param max_range_km: The maximum range of the bus on full charge (from parameters)
        """
        pass

class RangeConstraint(HardConstraint):
    """Enforces that the bus never runs out of battery range between consecutive points."""
    
    def is_valid(self, plan: List[str], bus: Bus, route: Route, max_range_km: float) -> bool:
        # Get sequence of nodes for the bus's direction (starts at origin endpoint, ends at destination endpoint)
        nodes_seq = route.get_nodes_in_direction(bus.direction)
        origin = nodes_seq[0]
        destination = nodes_seq[-1]
        
        # Build the sequence of actual stop points: origin -> plan stations -> destination
        stops = [origin] + plan + [destination]
        
        # Check distance between every consecutive pair of stops
        for i in range(len(stops) - 1):
            n1 = stops[i]
            n2 = stops[i+1]
            try:
                dist = route.get_distance(n1, n2)
            except ValueError:
                return False
                
            if dist > max_range_km:
                return False
        
        return True

class SequenceConstraint(HardConstraint):
    """Enforces that a bus visits stations strictly in sequential route order with no backtracking."""
    
    def is_valid(self, plan: List[str], bus: Bus, route: Route, max_range_km: float) -> bool:
        # Get all station IDs in direction of travel
        nodes_seq = route.get_nodes_in_direction(bus.direction)
        # Exclude origin and destination endpoints to get only stations in their traversal order
        stations_seq = [node for node in nodes_seq if node in route.stations]
        
        # The chosen plan's stations must be a strict subset of stations_seq in the exact same relative order.
        # This means as we iterate through plan, their indices in stations_seq must be strictly increasing.
        last_idx = -1
        for station in plan:
            if station not in stations_seq:
                return False
            curr_idx = stations_seq.index(station)
            if curr_idx <= last_idx:
                return False
            last_idx = curr_idx
            
        return True
