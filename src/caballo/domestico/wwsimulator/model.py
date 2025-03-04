from abc import ABC, abstractmethod
from copy import copy
from caballo.domestico.wwsimulator.streams import EXTERNAL_ARRIVALS, SERVICES_BASE
from pdsteele.des import rngs
import pdsteele.des.rvgs as des
error = 'index out of range'
distr_error = 'distribution not supported'
class Job():
    """
    A unit of work to be processed by the nodes in a simulation.
    """
    def __init__(self, class_id: int, job_id: int):
        self.class_id = class_id
        self.job_id = job_id
        self.service_time = None

    def class_id(self):
        return self.class_id

    def class_id(self, value):
        self.class_id = value

    def job_id(self):
        return self.job_id
    

class State():
    """
    Classe che definisce lo stato del sistema con una matrice 3x3 
    dove ogni riga rappresenta un nodo e ogni colonna una classe di job
    """
    def __init__(self, matrix: list, n_nodes: int = 3, n_classes: int = 3):
        self.matrix = matrix
        self.n_nodes = n_nodes
        self.n_classes = n_classes
    
    def update(self, node_class: tuple, increment: bool):
        """
        Metodo per incrementare o decrementare lo stato di un nodo
        """

        if node_class[1] > self.n_classes or node_class[0] > self.n_classes:
            raise ValueError(error)
        
        self.matrix[node_class[0]][node_class[1]] += 1 if increment else -1

    def get(self):
        """
        Metodo per ritornare la matrice completa dello stato
        """
        return self.matrix
    
    def get_node_state(self, node):
        """
        Metodo per ritornare lo stato di un singolo nodo
        """
        return self.matrix[node]
    
    def get_total_class(self, class_type):
        """
        Metodo per ritornare il numero totale di job in una certa classe nel sistema
        """
        if class_type > 3:
            raise ValueError(error)
        return sum([self.matrix[i][class_type] for i in range(self.n_nodes)])

    def get_num_jobs_in_node(self, node):
        node_index = node.node_map(node.id)
        num_jobs_in_node = sum(self.get_node_state(node_index))
        return num_jobs_in_node
    
class Server():
    """
    Classe che definisce un server all'interno di un nodo. Il server ha una capacità
    e una distribuzione di servizio.
    id: identificativo del server, può essere A, B, P
    capacity: capacità del server
    server_distribution: tupla con distribuzione di servizio e parametro della distribuzione
    """
    def __init__(self, capacity: int, server_distribution: str, prng_stream: int):
        self.capacity = capacity
        self.server_distribution = server_distribution
        self.prng_stream = prng_stream
    
    def get_service(self, params):
        rngs.selectStream(self.prng_stream)
        if self.server_distribution == 'exp':
            return des.Exponential(1.0 / params[0])
        else:
            raise ValueError(distr_error)


class Queue(ABC):
    def __init__(self, capacity: int, queue_params:list):
        self.id = id
        self.capacity = capacity
        self.queue_params = queue_params
    
    @abstractmethod
    def get_queue_time(self, job: Job, arrival_time: float):
        pass

    @abstractmethod
    def register_last_departure(self, job: Job, time: float):
        pass

    

class FIFOQueue(Queue):
    def __init__(self, capacity: int, queue_params:list):
        super().__init__(capacity, queue_params)
        self.last_departure = 0
        self.queue_time = 0
    
    def get_queue_time(self, job: Job, arrival_time: float):
        diff = self.last_departure - arrival_time
        # controllare se diff è positivo
        self.queue_time = diff if diff > 0 else 0.0
        return self.queue_time

    def register_last_departure(self, job: Job, time: float):
        self.last_departure = time

    
class PSQueue(Queue):
    def __init__(self, capacity: int, queue_params:list):
        super().__init__(capacity, queue_params)
    
    def get_queue_time(self, job: Job, arrival_time: float):
        return 0.0

    def register_last_departure(self, job: Job, time: float):
        pass

class Node():
    def __init__(self, id: str, service_rate: list, server:Server, queue:Queue):
        self.id = id
        self.server = server
        self.queue = queue
        self.service_rate = service_rate
        self.scheduled_departures = {}
        """
        Scheduled departure events by job id in service at this node
        """

    def get_service_class_rate(self, class_type):
        if class_type > 3:
            raise ValueError(error)
        
        return self.service_rate[class_type]
    
    def node_map(self, node_id):
        node_map = {'A': 0, 'B': 1, 'P': 2}
        if node_id not in node_map:
            raise ValueError(error)
        return node_map[node_id]

class Network():
    """
    A network is a collection of nodes that interact with each other to process jobs.
    """
    def __init__(self, nodes: list, state: State, job_arrival_distr: str, job_arrival_param: list):
        self.nodes = nodes
        """
        list of nodes in the network
        """
        self.state = state
        """
        State of the network during a simulation run
        """
        self.job_arrival_distr = job_arrival_distr
        """
        Distribution of job arrivals
        """
        self.job_arrival_param = job_arrival_param
        """
        Parameters of the job arrival distribution
        """

    def get_arrivals(self):
        rngs.selectStream(EXTERNAL_ARRIVALS)
        if self.job_arrival_distr == 'poisson':
            return des.Exponential(1.0 / self.job_arrival_param[0])
        else:
            raise ValueError(distr_error)
        
    def get_node(self, node_id):
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_state(self):
        return self.state.get()

    def get_node_state(self, node_id):
        node = self.get_node(node_id)
        return self.state.get_node_state(node.id)

    def get_total_class(self, class_type):
        return self.state.get_total_class(class_type)