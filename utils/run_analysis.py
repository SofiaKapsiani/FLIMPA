from PySide6.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PySide6.QtCore import Qt

from utils.qtread_custom import AnalysisThread
from utils.shared_data import SharedData
from utils.lifetime_cal import LifetimeData
from utils.errors import show_error_message

class Analysis:
    """Running the lifetime analysis"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.app = main_window.app 
        self.shared_info = SharedData()

    def run_phasor(self):
        # Check if self.results_dict is not empty
        if self.shared_info.results_dict:
            # Create a message box
            msg_box = QMessageBox(self.main_window)  # Use main_window as the parent
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("Recalculate Analysis")
            msg_box.setText("Would you like to keep the current analysis or recalculate everything?")
            msg_box.setEscapeButton(QMessageBox.Ok)
            keep_button = msg_box.addButton("Keep Current", QMessageBox.YesRole)
            recalculate_button = msg_box.addButton("Recalculate Everything", QMessageBox.NoRole)

            # Show the message box and get the user's response
            msg_box.exec()

            if msg_box.clickedButton() == recalculate_button:
                # If the user chooses to recalculate, clear self.results_dict
                self.shared_info.results_dict = {}
                self.shared_info.df_stats = {}

        # Check if reference file and raw data are provided
        if not self.shared_info.ref_files_dict:
            error_msg = QMessageBox(self.main_window)  # Use main_window as the parent
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("Error")
            error_msg.setText("Please provide reference file for analysis.")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec()
            return
        elif not self.shared_info.raw_data_dict:
            error_msg = QMessageBox(self.main_window)  # Use main_window as the parent
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("Error")
            error_msg.setText("Please provide raw data for analysis.")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec()
            return

        # Create a progress dialog
        self.progress_dialog = QProgressDialog("Analysing files...", "Cancel", 0, 100, self.main_window)  # Use main_window as the parent
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.canceled.connect(self.cancel_analysis)
        self.progress_dialog.show()

        # Create a thread to run the analysis
        self.lifetime_data = LifetimeData(self.main_window, self.app)
        self.analysis_thread = AnalysisThread(self.lifetime_data)

        # Connect signals and slots
        self.analysis_thread.progressUpdated.connect(self.update_progress)
        self.analysis_thread.analysisFinished.connect(self.on_analysis_finished)

        # Start the thread
        self.analysis_thread.start()

    def cancel_analysis(self):
        if self.analysis_thread.isRunning():
            self.analysis_thread.stop()
            self.progress_dialog.close()

    def closeEvent(self, event):
        if hasattr(self, 'analysis_thread') and self.analysis_thread.isRunning():
            self.analysis_thread.stop()
        event.accept()

    def update_progress(self, value, filename):
        self.progress_dialog.setValue(value)
        self.progress_dialog.setLabelText(f"Analysing file: {filename}")
        QApplication.processEvents()  # Keep the UI responsive

    def on_analysis_finished(self, results_dict):
        self.progress_dialog.close()  # Close the progress dialog when done
        self.shared_info.results_dict = results_dict
        try:
            self.main_window.analysis_finished()  # Call the main window's analysis_finished method
        except AttributeError as e:
            show_error_message(self.main_window, "Analysis Error", f"An unexpected error occurred during analysis: {e}")
