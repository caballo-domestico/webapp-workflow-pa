import json
import os

from caballo.domestico.wwsimulator import SIMULATION_FACTORY_CONFIG_PATH, STATISTICS_DIR
from caballo.domestico.wwsimulator.batchmeans import (BatchMeansInterceptor,
                                                      BatchMeansSimulation)
from caballo.domestico.wwsimulator.events import (ArrivalEvent, DepartureEvent,
                                                  Event, JobMovementEvent)
from caballo.domestico.wwsimulator.handlers import (
    ArrivalsGeneratorSubscriber, HandleFirstArrival)
from caballo.domestico.wwsimulator.output import (BusytimeEstimator, CompletionsEstimator,
                                                  ObservationTimeEstimator,
                                                  PopulationEstimator,
                                                  ResponseTimeEstimator,
                                                  )
from caballo.domestico.wwsimulator.replication import ReplicatedSimulation
from caballo.domestico.wwsimulator.simulation import Simulation, SimulationFactory

SEED = int("5E1BE110", 16) # :-*

def subscribe_estimators(simulation):
    simulation.scheduler.subscribe(JobMovementEvent, BusytimeEstimator())
    simulation.scheduler.subscribe(Event, ObservationTimeEstimator())
    simulation.scheduler.subscribe(DepartureEvent, CompletionsEstimator())
    simulation.scheduler.subscribe(JobMovementEvent, ResponseTimeEstimator())
    simulation.scheduler.subscribe(JobMovementEvent, PopulationEstimator())
    # simulation.scheduler.subscribe(ArrivalEvent, InterarrivalTimeEstimator())
    # simulation.scheduler.subscribe(DepartureEvent, ServiceTimeEstimator())
     

def get_output_file_path(simulation: Simulation):
    simulation_map = {'BatchMeansSimulation': 'BM_S', 'ReplicatedSimulation': 'Rep_S'}
    statistic_path = os.path.join(STATISTICS_DIR, simulation.study, type(simulation).__name__)
    simulation_name = simulation_map[type(simulation).__name__]
    if not os.path.exists(statistic_path):
        os.makedirs(statistic_path)
    output_file_path = os.path.join(statistic_path, "{}_{}_lambda={}_{}.csv".format(simulation.study, simulation_name, simulation.network.job_arrival_param[0], simulation.initial_seed))
    return output_file_path

def bm_main(experiment, lambda_val, seed):
    batch_size = experiment['batch_means']['batch_size']
    batch_num = experiment['batch_means']['batch_num']
    num_arrivals = batch_size * batch_num
    factory = SimulationFactory()

    simulation = factory.create(HandleFirstArrival(), experiment, lambda_val, seed=seed)
    bm_simulation = BatchMeansSimulation(simulation)

    simulation.scheduler.subscribe(ArrivalEvent, ArrivalsGeneratorSubscriber(num_arrivals))
    subscribe_estimators(simulation)
    
    simulation.scheduler.intercept(DepartureEvent, BatchMeansInterceptor(batch_size, batch_num, bm_simulation))

    output_file_path = get_output_file_path(bm_simulation)
    if not os.path.isfile(output_file_path):
        bm_simulation.run()
        bm_simulation.print_statistics(output_file_path)

def rep_main(experiment, lambda_val, seed):
    replicas = []
    factory = SimulationFactory()
    num_arrivals = experiment['batch_means']['batch_size']
    num_replicas = experiment['batch_means']['batch_num']
    for _ in range(num_replicas):
        replica = factory.create(HandleFirstArrival(), experiment, lambda_val, seed=seed)
        replica.scheduler.subscribe(ArrivalEvent, ArrivalsGeneratorSubscriber(num_arrivals))
        subscribe_estimators(replica)
        replicas.append(replica)
    simulation = ReplicatedSimulation(replicas)
    output_file_path = get_output_file_path(simulation)
    if not os.path.isfile(output_file_path):
        simulation.run()
        simulation.print_statistics(output_file_path)

def print_progress(part, total, msg=""):
    if total == 0:
        return
    progress = part / total * 100
    print(msg, end="")
    print(f"{progress:.0f}" + "%", end="\r")

if __name__ == "__main__":
    with open(SIMULATION_FACTORY_CONFIG_PATH, 'r') as file:
        data = json.load(file)
    i = 0
    j = 0
    experiments = data['exps']
    progress_message = None
    batch_size = None
    for experiment in experiments:
        simulation_study = experiment['simulation_study']
        lambda_values = experiment['arrival_distr']['params']
        print_progress(j, len(lambda_values) * len(experiments), )
        batch_size = len(lambda_values) * len(experiments)
        for lambda_val in lambda_values:
            
            progress_message = f"Simulation study {simulation_study:^15} with external arrival rate of {lambda_val:.2f} req/s: "
            print_progress(j, batch_size, progress_message)

            # batch mean
            bm_main(experiment, lambda_val, SEED)
            # replicated
            rep_main(experiment, lambda_val, SEED)

            j += 1
        i += 1
    print_progress(j, batch_size, progress_message) # last percentage update
    print("")  # newline




