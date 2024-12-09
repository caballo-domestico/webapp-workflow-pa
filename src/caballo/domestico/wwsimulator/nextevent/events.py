from abc import abstractmethod
from typing import Any, Callable, Dict, Iterable
from caballo.domestico.wwsimulator.model import Job, Network, Server


class EventContext():

    def __init__(self, event, network: Network, scheduler, statistics: Dict[str, Iterable[Any]]):
        self.event = event
        self.network = network
        self.scheduler = scheduler
        self.statistics = statistics

class EventHandler(Callable):
    def __init__(self):
        # unused constructor
        pass

    @abstractmethod
    def _handle(self, context: EventContext):
        pass

    def __call__(self, context: EventContext):
        self._handle(context)

class Event():
    """
    An event occurs at a specific simulation time and can change the simulation state.
    The exact effect of an event on the state is determined by the handler function.
    """
    def __init__(self, time: float, handler: EventHandler):
        self.time = time
        self.handle = handler

class JobMovementEvent(Event):
    """
    A job can move from one node of the network to another.
    """
    def __init__(self, time: float, handler: EventHandler, job: Job, server: Server):
        super().__init__(time, handler)
        self.job = job
        self.server = server

# nell'arrival il server è quello in cui sta arrivando il job
class ArrivalEvent(JobMovementEvent):
    def __init__(self, time: float, handler: EventHandler, job: Job, server: Server):
        super().__init__(time, handler, job, server)

# nella departure il server è quello da cui sta partendo il job
class DepartureEvent(JobMovementEvent):
    def __init__(self, time: float, handler: EventHandler, job: Job, server: Server):
        super().__init__(time, handler, job, server)

class StopEvent(Event):
    """
    A stop event signals the end of the simulation.
    """
    def __init__(self, time: float):
        super().__init__(time, _handle_stop)

def _handle_stop(context: EventContext):
    context.scheduler.stop = True
   