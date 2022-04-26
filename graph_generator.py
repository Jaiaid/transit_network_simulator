import re
import matplotlib.pyplot as plot

DATA_FILE_NAME = "event_log.txt"

REGEX_VEHICLE_EVENT_LINE_TYPE1 = r"^route (\d+) vehicle (\d+) ([a-z_]+) (\d+) at (\d+\.?\d*)"
REGEX_VEHICLE_EVENT_LINE_TYPE2 = r"^route (\d+) vehicle (\d+) ([a-z_]+) at (\d+\.?\d*)"
REGEX_WAITTIME = r"^Waiting time: (\d*\.\d+)"
REGEX_EVACTIME = r"^Total Evacuation Time: (\d*\.\d+)"
REGEX_TRIPCOUNT = r"^Number of trips: (\d+)"
REGEX_EVACUEECOUNT = r"^Number of evacuaees: (\d+)"
REGEX_RESULT_FILENAME = r"result(\d+).txt"


class GraphGenerator:
    def __init__(self):
        self.hourly_trip_completion_stat: dict[int, int] = {}
        self.hourly_trip_start_stat: dict[int, int] = {}
        self.hourly_speed_stat: dict[int, float] = {}

    def __analyze(self):
        with open(DATA_FILE_NAME) as log_fin:
            for logline in log_fin.readlines():
                logline = logline.split('\n')[0]

                result = re.search(REGEX_VEHICLE_EVENT_LINE_TYPE1, logline)
                if result is None:
                    result = re.search(REGEX_VEHICLE_EVENT_LINE_TYPE2, logline)
                if result is None:
                    continue

                route_id = int(result.groups()[0])
                vehicle_id = int(result.groups()[1])
                event_type = result.groups()[2]

                if event_type == "trip_start":
                    timestamp = float(result.groups()[3])
                    # hourly, hence 3600
                    hour = int(timestamp // 3600)
                    if hour not in self.hourly_trip_start_stat:
                        self.hourly_trip_start_stat[hour] = 1
                    else:
                        self.hourly_trip_start_stat[hour] += 1
                elif event_type == "trip_completion":
                    timestamp = float(result.groups()[3])
                    # hourly, hence 3600
                    hour = int(timestamp // 3600)
                    if hour not in self.hourly_trip_completion_stat:
                        self.hourly_trip_completion_stat[hour] = 1
                    else:
                        self.hourly_trip_completion_stat[hour] += 1
        # print(self.hourly_trip_start_stat)
        # print(self.hourly_trip_completion_stat)

    def generate(self):
        self.__analyze()

        fig_trip_start, ax_trip_start = plot.subplots()
        fig_trip_complete, ax_trip_complete = plot.subplots()

        ax_trip_start.bar([str(key) for key in self.hourly_trip_start_stat.keys()],
                          list(self.hourly_trip_start_stat.values()), color='maroon', width=0.4)
        ax_trip_complete.bar([str(key) for key in self.hourly_trip_completion_stat.keys()],
                             list(self.hourly_trip_completion_stat.values()), color='maroon', width=0.4)

        ax_trip_start.set_title("trip start hourly count")
        ax_trip_start.legend()
        ax_trip_start.set_xlabel("hour")
        ax_trip_start.set_ylabel("count")
        fig_trip_start.savefig("hourly_trip_start_barplot.png", dpi=300)

        ax_trip_complete.set_title("trip completion hourly count")
        ax_trip_complete.legend()
        ax_trip_complete.set_xlabel("hour")
        ax_trip_complete.set_ylabel("count")
        fig_trip_complete.savefig("hourly_trip_completion_barplot.png", dpi=300)

