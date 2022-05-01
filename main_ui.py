import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QMainWindow
)

from main_window_ui import Ui_MainWindow


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

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

    def start_simulation(self):
        pass

    def start_analysis(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
