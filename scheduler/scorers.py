from abc import ABC, abstractmethod
from typing import List, Dict, Any
from scheduler.models import Route, Bus

class SoftScorer(ABC):
    """Abstract class for pluggable soft scorers."""
    
    @abstractmethod
    def score(self, 
              plan: List[str], 
              bus: Bus, 
              route: Route, 
              simulated_trip: Dict[str, Any], 
              committed_schedules: List[Dict[str, Any]]) -> float:
        """
        Return a numeric penalty for a candidate plan (lower is better).
        
        :param plan: List of station IDs representing the chosen charging stations
        :param bus: The Bus object being scheduled
        :param route: The Route object
        :param simulated_trip: Dictionary containing simulated metrics of this trip:
                               {
                                   "total_trip_minutes": int,
                                   "total_wait_minutes": int,
                                   "events": List[Dict]
                               }
        :param committed_schedules: List of BusSchedule dicts for already-scheduled buses
        """
        pass

class IndividualWaitScorer(SoftScorer):
    """Minimizes the queue wait time for the individual bus."""
    
    def score(self, 
              plan: List[str], 
              bus: Bus, 
              route: Route, 
              simulated_trip: Dict[str, Any], 
              committed_schedules: List[Dict[str, Any]]) -> float:
        # Total wait time in minutes for this candidate trip
        return float(simulated_trip["total_wait_minutes"])

class OperatorFleetScorer(SoftScorer):
    """
    Minimizes the absolute deviation of this bus's projected trip time
    from the average trip time of committed buses of the same operator.
    """
    
    def score(self, 
              plan: List[str], 
              bus: Bus, 
              route: Route, 
              simulated_trip: Dict[str, Any], 
              committed_schedules: List[Dict[str, Any]]) -> float:
        # Find all committed schedules belonging to the same operator
        operator_trips = [
            sched["total_trip_minutes"]
            for sched in committed_schedules
            if sched["operator"].upper() == bus.operator.upper()
        ]
        
        if not operator_trips:
            # Cold start: first bus of this operator has 0 deviation penalty
            return 0.0
            
        avg_trip_time = sum(operator_trips) / len(operator_trips)
        deviation = abs(simulated_trip["total_trip_minutes"] - avg_trip_time)
        return float(deviation)

class OverallNetworkTimeScorer(SoftScorer):
    """Minimizes the total trip time for the bus."""
    
    def score(self, 
              plan: List[str], 
              bus: Bus, 
              route: Route, 
              simulated_trip: Dict[str, Any], 
              committed_schedules: List[Dict[str, Any]]) -> float:
        # Total trip duration from departure to arrival
        return float(simulated_trip["total_trip_minutes"])
