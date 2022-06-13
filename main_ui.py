import sys
import os
import time
import threading
import importlib.util

from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QMainWindow
)

from main_window_ui import Ui_MainWindow
from simulator import Simulator
from logger import Logger
from graph_generator import GraphGenerator


def check_module_existance(script_full_path: str, class_name: str) -> bool:
    module_path = script_full_path
    # extract module name by removing .py from basepath
    module_name = ".".join(os.path.basename(module_path).split(".")[:-1])

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    # try loading the class
    # if it exists, it will not give any error
    # otherwise it will throw exception, there maybe multiple error
    # that's why we are throwing exception rather than catch it and return false
    # TODO:
    # replace bool return with error code mechanism
    getattr(module, class_name)

    return True


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.simulation_thread = None
        self.analysis_thread = None

    def __check_and_inform_pymodule_load_status(self, script_full_path: str, class_name: str) -> bool:
        try:
            check_module_existance(script_full_path=script_full_path, class_name=class_name)
        except ModuleNotFoundError or AttributeError as _:
            self.update_message(
                "module not found error or attribute error in module loading, please check selected script"
            )
            self.enable_ui(change_simulate_button=True)
            return False
        except Exception as e:
            self.update_message(
                "unknown exception in module loading: {0}, please check selected script".format(e.__str__()))
            return False
        self.update_message("class {0} can be loaded successfully from {1}".format(class_name, script_full_path))
        return True

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

    def select_strategy_classes_script_path(self):
        filedialog = QFileDialog()
        filedialog.setFileMode(QFileDialog.AnyFile)
        filedialog.setViewMode(QFileDialog.List)
        filedialog.setNameFilter("python script (*.py)")
        if filedialog.exec_():
            filepath = filedialog.selectedFiles()[0]
            self.strategy_script_filepath_qlineedit.setText(filepath)

            if self.input_dir_path.text() is not None:
                self.update_dir_content(self.input_dir_path.text())

            self.__check_and_inform_pymodule_load_status(script_full_path=filepath, class_name="DispatchStrategy")
            self.__check_and_inform_pymodule_load_status(script_full_path=filepath, class_name="VehicleStrategy")

    def select_node_class_script_path(self):
        filedialog = QFileDialog()
        filedialog.setFileMode(QFileDialog.AnyFile)
        filedialog.setViewMode(QFileDialog.List)
        filedialog.setNameFilter("python script (*.py)")
        if filedialog.exec_():
            filepath = filedialog.selectedFiles()[0]
            self.node_script_filepath_qlineedit.setText(filepath)

            if self.input_dir_path.text() is not None:
                self.update_dir_content(self.input_dir_path.text())

            self.__check_and_inform_pymodule_load_status(script_full_path=filepath, class_name="Node")

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
        if self.simulate_button.text() == "stop":
            self.simulation_thread.stop()
            self.simulate_button.setText("simulate")
        else:
            try:
                self.simulation_progress_bar.reset()
                self.simulation_thread = SimulationThread(window_object=self,
                                                          duration=self.simulation_duration_slider.value())
                self.simulation_thread.start()
                self.update_message("simulation in progress...")
            except Exception as e:
                print(e)

    def start_analysis(self):
        self.analysis_thread = AnalysisThread(window_object=self, time_step=self.analysis_time_step_slider.value())
        try:
            self.update_message("analysis in progress...")
            self.analysis_thread.start()
        except Exception as e:
            print(e)

    def update_progress_bar(self, value: int):
        self.simulation_progress_bar.setValue(value)


class AnalysisThread(threading.Thread):
    def __init__(self, window_object: Window, time_step: int):
        super().__init__()
        self.time_step = time_step
        self.window_object = window_object

    def set_time_step(self, time_step: int):
        self.time_step = time_step

    def run(self):
        self.window_object.disable_ui(change_simulate_button=True)
        try:
            analyzer = GraphGenerator()
            analyzer.generate(avg_velocity_time_step_sec=self.time_step)
            self.window_object.update_message("graphs are saved in {0}".format(os.path.abspath(os.path.curdir)))
        except FileNotFoundError as e:
            self.window_object.update_message("{0}/event_log.txt not found".format(os.path.abspath(".")))
        except Exception as e:
            self.window_object.update_message(e.__str__())
        finally:
            self.window_object.enable_ui(change_simulate_button=True)


class SimulationThread(threading.Thread):
    def __init__(self, window_object: Window, duration: int):
        super().__init__()
        self.duration = duration
        self.window_object = window_object
        self.simulator: Simulator = Simulator()
        self.simulation_progress_observer_thread = None

    def set_duration(self, duration: int):
        self.duration = duration

    # TODO
    # find the strategy class from module and load automatically
    # currently class name is provided
    def run(self):
        try:
            self.window_object.disable_ui(change_simulate_button=True)

            try:
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

                # progress bar crash is solved
                # crash is solved by using signal and slot to avoid updating progress bar from another thread
                # signal is created and corresponding slot is implemented in Window class
                # from another thread signal is emitted to make sure update (slot execution) is done in main thread
                # https://wiki.qt.io/Qt_for_Python_Signals_and_Slots
                # https://stackoverflow.com/questions/71875808/how-to-update-value-in-progressbar-in-another-thread-in-qt-c
                # other widget update will be switched to signaling
                self.simulation_progress_observer_thread = SimulationProgressThread(
                    self.window_object, simulator=self.simulator, duration=self.duration)
                self.simulation_progress_observer_thread.start()

                Logger.init()
                try:
                    strategy_class_script_path = self.window_object.strategy_script_filepath_qlineedit.text()
                    node_class_script_path = self.window_object.node_script_filepath_qlineedit.text()
                    # provide datafile and prepare internal datastructure and environment
                    # they maybe provided in steps but maybe it will be easier to give one public method
                    self.simulator.simulate(
                        strategy_script_path=strategy_class_script_path,
                        node_script_path=node_class_script_path,
                        networkdata_filepath=network_filepath,
                        demanddata_filepath=demand_filepath,
                        fleetdata_filepath=fleet_filepath,
                        edgedata_filepath=edgecap_filepath,
                        stopdata_filepath=nodecap_filepath,
                        routedata_filepath=route_filepath,
                        perroutestopdata_filepath=routestop_filepath,
                        time_length=self.duration)
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

                Logger.close()

                self.window_object.update_message(
                    "simulating data from {0} is done".format(input_dir))
                self.window_object.update_message(
                    "events saved in {0}/event_log.txt".format(os.path.abspath(os.path.curdir)))
                # wait for progress bar thread exit
                self.simulation_progress_observer_thread.join()
            except Exception as e:
                self.window_object.update_message(e.__str__())
            finally:
                self.window_object.enable_ui(change_simulate_button=True)
        except Exception as e:
            print(e)

    def stop(self):
        self.simulator.stop_simulation()


class SimulationProgressThread(threading.Thread):
    def __init__(self, window_object: Window, simulator: Simulator, duration: int):
        super().__init__()
        self.duration = duration
        self.simulator_object = simulator
        self.window_object = window_object
        self.exit_flag = False
        self.done = False

    def run(self):
        try:
            while self.window_object.simulation_progress_bar.value() < 100 and not self.exit_flag:
                self.window_object.simulation_progress_bar.valueChanged.emit(
                    int((self.simulator_object.get_time() * 100)//self.duration))
                # adding sleep to reduce cpu usage in busy loop
                time.sleep(0.01)
            self.done = True
        except Exception as e:
            print(e)

    def stop(self):
        self.exit_flag = True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
