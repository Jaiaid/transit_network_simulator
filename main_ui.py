import sys
import os
import time
import threading

from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QMainWindow
)

from main_window_ui import Ui_MainWindow
from simulator import Simulator
from logger import Logger
from graph_generator import GraphGenerator


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

    def disable_ui(self, change_simulate_button: bool):
        if change_simulate_button:
            self.simulate_button.setDisabled(True)
        self.analysis_time_step_slider.setDisabled(True)
        self.simulation_duration_slider.setDisabled(True)
        self.analyze_button.setDisabled(True)
        self.dir_browse_button.setDisabled(True)

    def enable_ui(self, change_simulate_button: bool):
        if change_simulate_button:
            self.simulate_button.setDisabled(False)
        self.analysis_time_step_slider.setDisabled(False)
        self.simulation_duration_slider.setDisabled(False)
        self.analyze_button.setDisabled(False)
        self.dir_browse_button.setDisabled(False)

    def update_message(self, message: str):
        self.app_runtime_info_area.append(message)

    def simulation_duration_update(self, value: int):
        self.simulation_duration_label.setText("{0} time unit".format(value))

    def analysis_time_step_update(self, value: int):
        self.analysis_time_step_label.setText("{0} time unit".format(value))

    def select_directory_path(self):
        filedialog = QFileDialog()
        filedialog.setFileMode(QFileDialog.DirectoryOnly)
        filedialog.setViewMode(QFileDialog.List)
        if filedialog.exec_():
            dirname = filedialog.selectedFiles()[0]
            self.input_dir_path.setText(dirname)

    def select_dispatcher_strategy_path(self):
        filedialog = QFileDialog()
        filedialog.setFileMode(QFileDialog.AnyFile)
        filedialog.setViewMode(QFileDialog.List)
        filedialog.setNameFilter("python script (*.py)")
        if filedialog.exec_():
            filename = filedialog.selectedFiles()[0]
            self.dispatcher_strategy_filepath.setText(filename)

            if self.input_dir_path.text() is not None:
                self.update_dir_content(self.input_dir_path.text())

    def select_vehicle_strategy_path(self):
        filedialog = QFileDialog()
        filedialog.setFileMode(QFileDialog.AnyFile)
        filedialog.setViewMode(QFileDialog.List)
        filedialog.setNameFilter("python script (*.py)")
        if filedialog.exec_():
            filename = filedialog.selectedFiles()[0]
            self.vehicle_strategy_filepath.setText(filename)

            if self.input_dir_path.text() is not None:
                self.update_dir_content(self.input_dir_path.text())

    def update_dir_content(self, content: str):
        self.directory_content.clear()
        self.app_runtime_info_area.clear()

        filelist = os.listdir(content)
        all_found = True
        for necessary_filename in ["network.txt", "route.txt", "demand.txt", "fleet.txt"]:
            if necessary_filename not in filelist:
                self.update_message("{0} file not found in {1} directory".format(necessary_filename, content))
                all_found = False

        if all_found:
            self.update_message("all_necessary input files are found")
            for filename in os.listdir(content):
                self.directory_content.append(filename)
        self.simulate_button.setDisabled(not all_found)

    def start_simulation(self):
        self.simulation_progress_bar.setValue(0)
        simulation_thread = SimulationThread(window_object=self, duration=self.simulation_duration_slider.value())
        simulation_thread.start()

    def start_analysis(self):
        analysis_thread = AnalysisThread(window_object=self, time_step=self.analysis_time_step_slider.value())
        analysis_thread.start()


class AnalysisThread(threading.Thread):
    def __init__(self, window_object: Window, time_step: int):
        super().__init__()
        self.time_step = time_step
        self.window_object = window_object

    def run(self):
        self.window_object.disable_ui(change_simulate_button=False)
        try:
            analyzer = GraphGenerator()
            analyzer.generate(avg_velocity_time_step_sec=self.time_step)
            self.window_object.update_message("graphs are saved in {0}".format(os.path.abspath(os.path.curdir)))
        except FileNotFoundError as e:
            self.window_object.update_message("{0}/event_log.txt not found".format(os.path.abspath(".")))
        except Exception as e:
            self.window_object.update_message(e.__str__())
        finally:
            self.window_object.enable_ui(change_simulate_button=False)


class SimulationThread(threading.Thread):
    def __init__(self, window_object: Window, duration: int):
        super().__init__()
        self.duration = duration
        self.window_object = window_object

    def run(self):
        self.window_object.disable_ui(change_simulate_button=True)

        try:
            simulation_progress_observer_thread = None
            input_dir = self.window_object.input_dir_path.text()

            nodecap_filepath = "{0}/stopcap.txt".format(input_dir)
            edgecap_filepath = "{0}/edgecap.txt".format(input_dir)
            network_filepath = "{0}/network.txt".format(input_dir)
            demand_filepath = "{0}/demand.txt".format(input_dir)
            fleet_filepath = "{0}/fleet.txt".format(input_dir)
            route_filepath = "{0}/route.txt".format(input_dir)
            routestop_filepath = None

            if os.path.exists("{0}/route_stops.txt".format(input_dir)):
                routestop_filepath = "{0}/route_stops.txt".format(input_dir)

            # init necessary class and modules
            simulator: Simulator = Simulator()

            try:
                simulator.load_strategy(
                    dispatcher_strategy_full_import_string=
                    self.window_object.dispatcher_strategy_filepath.text()+".DispatchStrategy",
                    vehicle_strategy_full_import_string=
                    self.window_object.vehicle_strategy_filepath.text()+".VehicleStrategy")
            except ModuleNotFoundError or AttributeError as e:
                self.window_object.update_message(
                    "module not found error or attribute error in module loading: {0}, discontinuing simulation".
                        format(e.__str__())
                )
                self.window_object.enable_ui(change_simulate_button=True)
                return
            except Exception as e:
                self.window_object.update_message(
                    "unknown exception in module loading: {0}, discontinuing simulation".format(e.__str__()))
                self.window_object.enable_ui(change_simulate_button=True)
                return

            # provide datafile and prepare internal datastructure and environment
            simulator.load_data(
                networkdata_filepath=network_filepath,
                demanddata_filepath=demand_filepath,
                routedata_filepath=route_filepath,
                fleetdata_filepath=fleet_filepath,
                edgedata_filepath=edgecap_filepath,
                stopdata_filepath=nodecap_filepath,
                perroutestopdata_filepath=routestop_filepath
            )

            simulation_progress_observer_thread = SimulationProgressThread(
                self.window_object, simulator=simulator, duration=self.duration)
            simulation_progress_observer_thread.start()

            Logger.init()
            simulator.simulate(
                dispatcher_strategy_full_import_string=
                self.window_object.dispatcher_strategy_filepath.text()+".DispatchStrategy",
                vehicle_strategy_full_import_string=
                self.window_object.vehicle_strategy_filepath.text()+".VehicleStrategy",
                time_length=self.duration
            )
            Logger.close()

            self.window_object.update_message(
                "simulating data from {0} is done".format(input_dir))
            self.window_object.update_message(
                "events saved in {0}/event_log.txt".format(os.path.abspath(os.path.curdir)))
        except Exception as e:
            self.window_object.update_message(e.__str__())
        finally:
            self.window_object.enable_ui(change_simulate_button=True)
            if simulation_progress_observer_thread is not None:
                simulation_progress_observer_thread.exit()


class SimulationProgressThread(threading.Thread):
    def __init__(self, window_object: Window, simulator: Simulator, duration: int):
        super().__init__()
        self.duration = duration
        self.simulator_object = simulator
        self.window_object = window_object
        self.exit_flag = False

    def run(self):
        while self.window_object.simulation_progress_bar.value() < 100 and not self.exit_flag:
            self.window_object.simulation_progress_bar.setValue((self.simulator_object.get_time() * 100)//self.duration)
            time.sleep(0.01)

    def exit(self):
        self.exit_flag = True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
