import simpy

from logger import Logger


class Node(simpy.Resource):
    # initiate by providing a dictionary with demand information
    # the dictionary has key with value of destination node ide and corresponding value is number of passengers
    def __init__(self, node_id: int, env: simpy.Environment, capacity: int, dest_id_passenger_dict: dict[int, int]):
        self.id = node_id
        self.dest_id_passenger_dict = dest_id_passenger_dict
        self.env = env
        super().__init__(env, capacity)

    # return the demand information as a dictionary
    # the dictionary has key with value of destination node ide and corresponding value is number of passengers
    def get_demand_dict(self) -> dict[int, int]:
        return self.dest_id_passenger_dict

    # drain count amount of passenger from input dest id
    # this is supposed to be called by vehicle and that vehicle should provide its id and route id for log purpose
    # should return value of how much passenger can be boarded
    # for example count number of passenger is not available
    # given default implementation provides as much as passenger available and reduce passenger from its pool
    def drain(self, route_id: int, vehicle_id: int, dest_id: int, count: int) -> int:
        boarding = 0
        if dest_id in self.dest_id_passenger_dict:
            boarding = min(count, self.dest_id_passenger_dict[dest_id])
            Logger.log(
                "route {0} vehicle {1} boarding {2} passenger for {3} from {4} at {5}".format(
                    route_id, vehicle_id, boarding, dest_id, self.id, self.env.now)
            )
            self.dest_id_passenger_dict[dest_id] -= boarding

        return boarding

    # currently unused method
    def fill(self, dest_id_passenger_inc_dict: dict[int, int]):
        pass

    # get demand exists in this node to a destination
    # if no demand to that destination, zero is returned
    def get_demand_to(self, dest_id) -> int:
        if dest_id in self.dest_id_passenger_dict:
            return self.dest_id_passenger_dict[dest_id]
        return 0
