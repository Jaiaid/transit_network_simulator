import simpy
from vehicle import Vehicle


class Fleet:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.vehicle_dict: dict[int, Vehicle] = {}

    def size(self):
        return len(self.vehicle_dict)

    def load_data(self, filepath:str):
        with open(filepath) as fin:
            vehicle_id = 0
            for line in fin.readlines():
                tokens = line.split()

                name = tokens[0]
                capacity = int(tokens[1])
                length = float(tokens[2])
                speed = float(tokens[3])
                count = int(tokens[4])

                for i in range(count):
                    self.vehicle_dict[vehicle_id] = Vehicle(vehicle_id=vehicle_id, capacity=capacity, length=length,
                                                            speed=speed, env=self.env)
                    vehicle_id += 1
