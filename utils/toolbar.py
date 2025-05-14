from PySide6.QtWidgets import (QStatusBar, QMenuBar, QFileDialog, QInputDialog, QFileDialog, QLineEdit, QLabel,QPushButton,
                               QProgressDialog, QApplication, QMessageBox, QComboBox, QVBoxLayout, QDialogButtonBox, QDialog)
from PySide6.QtGui import QDoubleValidator

from PySide6.QtCore import Qt, QTimer
import numpy as np
from pathlib import Path
from utils.lifetime_cal import LifetimeData
from utils.mainwindow import *
from utils.shared_data import SharedData
from  utils import save_data 
from utils.plot_imgs import PlotImages
from utils.errors import DataProcessingError

class ToolBarComponents:
    def __init__(self, main_window, app):
        self.main_window = main_window
        self.app = app
        self.shared_info = SharedData()

        self.plotImages = PlotImages(self.main_window)
        self.setup_menu()
        self.setup_statusbar()


    def setup_menu(self):
        # set up navigation bar
        menu_bar = QMenuBar(self.main_window)
        self.main_window.setMenuBar(menu_bar)
        self.data_condition = "None"

        # file option
        file_menu = menu_bar.addMenu("&Load data")
        menu_bar.setStyleSheet("""
                               QMenuBar::item {color: rgb(255,255,255);}
                               """)
        # import data
        import_data = file_menu.addAction("Import raw data")
        import_data.triggered.connect(self.file_manager)
        # import data by condition
        import_condition = file_menu.addAction("Import raw data by condition")
        import_condition.triggered.connect(self.enter_files_by_cond)
        # import ref files
        
        file_menu.addSeparator()
        import_masks = file_menu.addAction("Import raw data with manual masks")
        import_masks.triggered.connect(self.load_masks)
        import_masks_cond = file_menu.addAction("Import raw data by condition with manual masks")
        import_masks_cond.triggered.connect(self.load_masks_cond)
        file_menu.addSeparator()

        # quit application
        #quit_action = file_menu.addAction("Quit")
        #quit_action.triggered.connect(self.quit_app)

        file_menu = menu_bar.addMenu("&Reference")
        import_ref = file_menu.addAction("Import reference file")
        import_ref.triggered.connect(self.load_ref_file)
        import_ref = file_menu.addAction("Import IRF")
        import_ref.triggered.connect(self.load_irf_file)

        # save data
        file_menu = menu_bar.addMenu("&Save")
        save_tau = file_menu.addAction("Save lifetime maps")
        save_tau.triggered.connect(self.save_tau_maps)
        save_gallery_tau = file_menu.addAction("Save lifetime gallery")
        save_gallery_tau.triggered.connect(self.save_gallery_images)
        file_menu.addSeparator()

        save_int_single = file_menu.addAction("Save intensity images")
        save_int_single.triggered.connect(self.save_intensity)
        save_int_gallery = file_menu.addAction("Save intensity gallery")
        save_int_gallery.triggered.connect(self.save_gallery_intensity)
        file_menu.addSeparator()

        save_phasor = file_menu.addAction("Save transparent phasor plot")
        save_phasor.triggered.connect(self.save_phasor_transparent)
        save_violin = file_menu.addAction("Save transparent violin plot")
        save_violin.triggered.connect(self.save_violin_transparent)
        file_menu.addSeparator()
        export_cv = file_menu.addAction("Export lifetime values table")
        export_cv.triggered.connect(self.save_csv)
        
    def setup_statusbar(self):
        self.main_window.setStatusBar(QStatusBar(self.main_window))

    def quit_app(self):
        self.app.quit()

    def enter_files(self):
        fnames, _ = QFileDialog.getOpenFileNames(self.main_window, "Select one or more files to open")  # Adjust the title as needed
        return fnames
    
    def enter_files_by_cond(self):
        # show all conditions besides "reference"
        previous_conditions = list(set(
            file_info['condition'] 
            for file_info in self.shared_info.raw_data_dict.values() 
            if file_info['condition'] != "reference"
        ))
    
        # Create and display the input dialog
        dialog = ConditionInputDialog(previous_conditions, self.main_window)
        if dialog.exec() == QDialog.Accepted:
            condition = dialog.getCondition()
            if condition:
                self.data_condition = condition
                fnames = self.file_manager()

    def get_float_input(self):
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Input Required")

        layout = QVBoxLayout(dialog)

        label = QLabel("Enter the bin width (in ns):", dialog)
        layout.addWidget(label)

        # Create a QLineEdit and set a QDoubleValidator for non-negative values and many decimal places
        line_edit = QLineEdit(dialog)
        validator = QDoubleValidator(0.0, 2.0, 50)  # Non-negative range, 10 decimal places
        validator.setNotation(QDoubleValidator.StandardNotation)
        line_edit.setValidator(validator)
        layout.addWidget(line_edit)

        # Create an "Estimate" button
        estimate_button = QPushButton("Estimate", dialog)
        layout.addWidget(estimate_button)

        # Create dialog buttons (OK and Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        layout.addWidget(buttons)

        # Connect signals
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        def estimate_bin_width():
            # Set the bin width to "estimate"
            line_edit.setText("estimate")
            # Show a warning message
            QMessageBox.warning(dialog, "Warning", 
                "You have selected 'estimate' for the bin width. This will be calculated as:\n"
                "bin width = 1 / (laser repetition rate × bin number).\n\n"
                "Please note that this estimation may lead to inaccurate results depending on your data acquisition settings. ")
            
        estimate_button.clicked.connect(estimate_bin_width)

        if dialog.exec() == QDialog.Accepted:
            # Check if user selected "estimate"
            if line_edit.text() == "estimate":
                return "estimate", True
            else:
                return float(line_edit.text()), True
        else:
            return None, False
            
        
    def file_manager(self):
        # Use getOpenFileNames for selecting multiple files
        fnames, _ = QFileDialog.getOpenFileNames(self.main_window, "Select one or more files to open")  # Adjust the title as needed
        if not fnames:
            return  # Cancel if no files are selected

        # channel used when loading .ptu files
        self.shared_info.ptu_channel = None
        self.shared_info.ptu_time_binning = None # option for binning time dimetion in ptu files for faster data analysis

        # Create a progress dialog
        progress_dialog = QProgressDialog("Loading files...", "", 0, len(fnames), self.main_window)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)

        # Disable the close button and remove the cancel button
        progress_dialog.setCancelButton(None)
        #progress_dialog.setWindowFlag(Qt.WindowCloseButtonHint, False)

        bin_width = None  # Initialize bin_width variable to store the user input

        try:
            for i, fname in enumerate(fnames):  # Iterate through the selected files
                if fname:
                    # Update the progress dialog
                    progress_dialog.setValue(i)
                    progress_dialog.setLabelText(f"Loading file {i+1} of {len(fnames)}")
                    QApplication.processEvents()  # Process events to keep the UI responsive

                    # Check if the file is a .tif or .tiff and if bin_width is already set
                    if fname.lower().endswith(('.tif', '.tiff')) and bin_width is None:
                        # Prompt the user for bin_width only once
                        bin_width, ok = self.get_float_input()
                        if not ok or bin_width is None:
                            break  # If the user cancels or no valid input, exit

                    # Assuming you have a mechanism to process and display each file
                    data, t_series = LifetimeData(self.main_window, self.app).load_raw_data(fname, bin_width,  sample_count = i)

                    filename = Path(fname).stem
                    # check if entry is duplicate and if so rename it
                    filename = self.handle_duplicates(filename)

                    self.shared_info.raw_data_dict[filename] = {"data": data, "t_series": t_series, "condition": self.data_condition, "masked_data": None, 
                                                                "mask_arr": None, "analyse": "yes"}
                    self.shared_info.config["selected_file"] = filename
                    self.plotImages.visualise_image(intensity_image=data.sum(axis=0), filename=filename)

                    self.main_window.activateWindow()  # Regain focus after files are loaded
                    self.main_window.raise_()  # Bring the window to the front

                    # Check if the user has canceled the operation
                    if progress_dialog.wasCanceled():
                        break

            progress_dialog.setValue(len(fnames))  # Ensure the progress dialog is complete
        except Exception as e:
            progress_dialog.close()  # Close the progress dialog if an error occurs
            raise  # Re-raise the exception to be handled elsewhere if needed

        self.data_condition = "None"
        return fnames


    def load_masks(self):
        # Select one or more files to open
        fnames, _ = QFileDialog.getOpenFileNames(self.main_window, "Select one or more files to open")
        if not fnames:
            return  # Cancel if no files are selected

        # Select the folder where manual masks are stored
        masks_dir = QFileDialog.getExistingDirectory(self.main_window, "Select the folder where manual masks are stored")
        if not masks_dir:
            return  # Cancel if no directory is selected

        print([Path(x).stem for x in fnames], masks_dir)

        # Create a progress dialog
        progress_dialog = QProgressDialog("Loading mask files...", "", 0, len(fnames), self.main_window)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)

        # Disable the close button and remove the cancel button
        progress_dialog.setCancelButton(None)
        #progress_dialog.setWindowFlag(Qt.WindowCloseButtonHint, False)
        bin_width = None  # Initialize bin_width variable to store the user input

        try:
            for i, fname in enumerate(fnames):  # Iterate through the selected files
                if fname:
                    # Update the progress dialog
                    progress_dialog.setValue(i)
                    progress_dialog.setLabelText(f"Loading file {i+1} of {len(fnames)}")
                    QApplication.processEvents()  # Process events to keep the UI responsive

                    # Check if the file is a .tif or .tiff and if bin_width is already set
                    if fname.lower().endswith(('.tif', '.tiff')) and bin_width is None:
                        # Prompt the user for bin_width only once
                        bin_width, ok = self.get_float_input()
                        if not ok or bin_width is None:
                            break  # If the user cancels or no valid input, exit
                        
                    # Assuming you have a mechanism to process and display each file
                    data, t_series = LifetimeData(self.main_window, self.app).load_raw_data(fname, bin_width, sample_count = i)
                    
                    filename_original = Path(fname).stem
                    masked_data, mask_arr = LifetimeData(self.main_window, self.app).mask_data(masks_dir, filename_original, data)
                    
                    # Check if entry is duplicate and if so rename it
                    filename = self.handle_duplicates(filename_original)

                    self.shared_info.raw_data_dict[filename] = {"data": data, "t_series": t_series, "condition": self.data_condition, "masked_data": masked_data, 
                                                                "mask_arr": mask_arr, "analyse": "yes"}
                    self.shared_info.config["selected_file"] = filename
                    self.plotImages.visualise_image(intensity_image=data.sum(axis=0), filename=filename)
                    
                    self.main_window.activateWindow()  # Regain focus after files are loaded
                    self.main_window.raise_()  # Bring the window to the front

                    # Check if the user has canceled the operation
                    if progress_dialog.wasCanceled():
                        break

            progress_dialog.setValue(len(fnames))  # Ensure the progress dialog is complete
        except Exception as e:
            progress_dialog.close()  # Close the progress dialog if an error occurs
            raise  # Re-raise the exception to be handled elsewhere if needed
        
        self.data_condition = "None"
        return fnames
        

    def load_masks_cond(self):
        previous_conditions = list(set(file_info['condition'] for file_info in self.shared_info.raw_data_dict.values()))
    
        # Create and display the input dialog
        dialog = ConditionInputDialog(previous_conditions, self.main_window)
        if dialog.exec() == QDialog.Accepted:
            condition = dialog.getCondition()
            if condition:
                self.data_condition = condition
                fnames = self.load_masks()

    def handle_duplicates(self, filename):
        """Function to rename duplicate entries"""
        base_filename = filename
        count = 1
        while filename in self.shared_info.raw_data_dict:
            filename = f"{base_filename}_{count}"
            count += 1
        return filename

    def load_ref_file(self):
        fname, _ = QFileDialog.getOpenFileName(self.main_window," Selet a reference file to open")
        self.shared_info.ptu_channel = None # set ptu channels info to None as the data may be stored in a different channel
        self.shared_info.ptu_time_binning = None # option for binning time dimetion in ptu files for faster data analysis

        bin_width = None
        # Create a progress dialog
        progress_dialog = QProgressDialog("Loading reference file...", "", 0, 1, self.main_window)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)

        # Disable the close button and remove the cancel button
        progress_dialog.setCancelButton(None)
        #progress_dialog.setWindowFlag(Qt.WindowCloseButtonHint, False)

        bin_width = None  # Initialize bin_width variable to store the user input

        try:
            
            progress_dialog.setValue(0)
            QApplication.processEvents()  # Process events to keep the UI responsive

            if fname.lower().endswith(('.tif', '.tiff')) and bin_width is None:
                # Prompt the user for bin_width only once
                bin_width, ok = self.get_float_input()
                if not ok or bin_width is None:
                    return  # If the user cancels or no val
        
            ref_data,t_series = LifetimeData(self.main_window, self.app).load_raw_data(fname, bin_width, data_type="reference", sample_count = 0)
            
            filename = Path(fname).stem
            # updated reference bins based on time channels of reference file
            self.shared_info.ref_files_dict[filename] = {"ref_data":ref_data, "t_series":t_series, "bins_ref": ref_data.shape[0] }  # Assuming you want to store the full path
            self.main_window.parameters_data.update_ref_file(list(self.shared_info.ref_files_dict.keys()))
            self.shared_info.raw_data_dict[filename] = {"data": ref_data, "t_series": t_series, "condition": "reference", "masked_data": None, 
                                                                    "mask_arr": None, "analyse": "no"}
            # only set the reference file as "selected file" if no other file has been loaded
            if self.shared_info.config["selected_file"] == "None":
                self.shared_info.config["selected_file"] = filename
            self.plotImages.visualise_image(intensity_image=ref_data.sum(axis=0), filename=filename)
            

            self.main_window.activateWindow()  # Regain focus after files are loaded
            self.main_window.raise_()  # Bring the window to the front


            progress_dialog.setValue(1)  # Ensure the progress dialog is complete
        except Exception as e:
            progress_dialog.close()  # Close the progress dialog if an error occurs
            raise  # Re-raise the exception to be handled elsewhere if needed

        

    def load_irf_file(self):
        fname, _ = QFileDialog.getOpenFileName(self.main_window," Selet a reference file to open")

        if fname.lower().endswith('.csv'):
            # user warning when a .csv IRF is used
            self.show_irf_warning(data_type="csv")
        elif fname.lower().endswith('.sdt'):
            # user warning when a .csv IRF is used
            self.show_irf_warning(data_type="sdt")
            
        ref_data,t_series = LifetimeData(self.main_window, self.app).load_irf(fname)
        filename = Path(fname).stem

        self.shared_info.ref_files_dict[filename] = {"ref_data":ref_data, "t_series":t_series, "bins_ref" : 1}  # Assuming you want to store the full path
        self.main_window.parameters_data.update_ref_file(list(self.shared_info.ref_files_dict.keys()))
    
    def show_irf_warning(self, data_type):
        # Create a message box
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("IRF Import Warning")
        
        # Format the message with bullet points
        if data_type == "csv":
            message = """
            <p>Please use a reference file instead of an IRF where possible.<br>
            Using an IRF can lead to less accurate results.</p>
            <p>If you choose to continue, please confirm the following:</p>
            <ul>
                <li>The full IRF is provided (no cropping).</li>
                <li>The first column contains time (in seconds).</li>
                <li>The second column contains the IRF signal.</li>
                <li>No additional columns are included.</li>
                <li>No columns titles are included.</li>
            </ul>
            """
        elif data_type == "sdt":
            message = """
            <p>Please use a reference file instead of an IRF where possible.<br>
            Using an IRF can lead to less accurate results.</p>"""
            
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        # Show the message box
        response = msg_box.exec()
        
        # Handle response if needed
        if response != QMessageBox.Ok:
            raise DataProcessingError("Channel selection cancelled by user.")
        
        
    # save error message
    def save_error_message(self, title, message):
        """
        Show an error message.
        
        Parameters:
        title (str): The title of the error message box.
        message (str): The message to be displayed.
        """
        error_msg = QMessageBox(self.main_window)
        error_msg.setIcon(QMessageBox.Warning)
        error_msg.setWindowTitle(title)
        error_msg.setText(message)
        error_msg.setStandardButtons(QMessageBox.Ok)
        error_msg.exec()

    
    def save_tau_maps(self):
        if not self.shared_info.results_dict:
            self.save_error_message("Error", "No data has been generated, please run phasor analysis first.")
            return

        # choose which lifetime to save
        items = ["M", "phi", "average"]
        item, ok = QInputDialog.getItem(self.main_window, "Save Lifetime Image", "Select lifetime to save:", items, 2, False)
        if ok and item:
            lifetime_type = item
        else:
            return

        output_dir = QFileDialog.getExistingDirectory(self.main_window, "Select the folder to save the lifetime maps")
        if output_dir:
            # Show the "Saving data..." progress dialog
            progress_dialog = QProgressDialog("Saving data...", "", 0, 0, self.main_window)
            progress_dialog.setWindowTitle("Saving Data")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setCancelButton(None)
            progress_dialog.show()

            # Process events to ensure the dialog is shown
            QApplication.processEvents()

            # Add a small delay to ensure the dialog displays correctly
            QTimer.singleShot(100, lambda: save_data.save_tau(output_dir, progress_dialog, lifetime_type, self.shared_info.results_dict, self.shared_info.config,))

        else:
            return

    def save_gallery_images(self):
        if not self.shared_info.results_dict:
            self.save_error_message("Error", "No data has been generated, please run phasor analysis first.")
            return

        output_dir = QFileDialog.getExistingDirectory(self.main_window, "Select the folder to save the gallery images")
        print(output_dir)
        
        if output_dir:
            # Prompt the user for the file name
            text, ok = QInputDialog.getText(self.main_window, "Save File", "Enter file name:", QLineEdit.Normal, "lifetime_gallery")
            if ok and text:
                file_name = text
            else:
                return
            
            # Show the "Saving data..." progress dialog
            progress_dialog = QProgressDialog("Saving data...", "", 0, 0, self.main_window)
            progress_dialog.setWindowTitle("Saving Data")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setCancelButton(None)
            progress_dialog.show()

            # Process events to ensure the dialog is shown
            QApplication.processEvents()

            # Add a small delay to ensure the dialog displays correctly
            QTimer.singleShot(100, lambda: save_data.save_gallery_view(output_dir, progress_dialog, file_name, self.shared_info.results_dict, self.shared_info.config, ))
            
            
        else:
            return
    
    def save_gallery_intensity(self):
        if not self.shared_info.results_dict:
            self.save_error_message("Error", "No data has been generated, please run phasor analysis first.")
            return

        output_dir = QFileDialog.getExistingDirectory(self.main_window, "Select the folder to save the intensity gallery")
        print(output_dir)
       
        if output_dir:
            # Prompt the user for the file name
            text, ok = QInputDialog.getText(self.main_window, "Save File", "Enter file name:", QLineEdit.Normal, "intensity_gallery")
            if ok and text:
                file_name = text
            else:
                return
            
            progress_dialog = QProgressDialog("Saving data...", "", 0, 0, self.main_window)
            progress_dialog.setWindowTitle("Saving Data")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setCancelButton(None)
            progress_dialog.show()

            # Process events to ensure the dialog is shown
            QApplication.processEvents()

            # Add a small delay to ensure the dialog displays correctly
            QTimer.singleShot(100, lambda: save_data.save_gallery_int_view(output_dir, progress_dialog, file_name, self.shared_info.results_dict, self.shared_info.config ))
            
           
        else:
            return

    def save_intensity(self):
        if not self.shared_info.intensity_img_dict:
            self.save_error_message("Error", "No data loaded, please add data first.")
            return

        output_dir = QFileDialog.getExistingDirectory(self.main_window, "Select the folder to save the intensity images")
        print(output_dir)
        
        if output_dir:
            progress_dialog = QProgressDialog("Saving data...", "", 0, 0, self.main_window)
            progress_dialog.setWindowTitle("Saving Data")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setCancelButton(None)
            progress_dialog.show()

            # Process events to ensure the dialog is shown
            QApplication.processEvents()

            # Add a small delay to ensure the dialog displays correctly
            QTimer.singleShot(100, lambda: save_data.save_intensity_images(output_dir, progress_dialog, self.shared_info.intensity_img_dict, self.shared_info.raw_data_dict, self.shared_info.config))
            
        else:
            return
    
    def save_phasor_transparent(self):
        output_dir = QFileDialog.getExistingDirectory(self.main_window, "Select the folder to save the phasor plot")
        print(output_dir)
        
        if output_dir:
            # Show the "Saving data..." progress dialog
            progress_dialog = QProgressDialog("Saving data...", "", 0, 0, self.main_window)
            progress_dialog.setWindowTitle("Saving Data")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setCancelButton(None)
            progress_dialog.show()

            # Process events to ensure the dialog is shown
            QApplication.processEvents()

            # Add a small delay to ensure the dialog displays correctly
            QTimer.singleShot(100, lambda: self._save_phasor_transparent(progress_dialog, output_dir))
        else:
            return

    def _save_phasor_transparent(self, progress_dialog, output_dir):
        # Save the phasor plot
        try:
            save_data.save_phasor_plot(output_dir, self.shared_info.results_dict, self.shared_info.phasor_settings, self.shared_info.config["frequency"])
            save_data.save_phasor_plot_condition(output_dir, self.shared_info.results_dict, self.shared_info.phasor_settings, self.shared_info.config["frequency"])
        finally:
            # Close the progress dialog after saving is complete
            progress_dialog.close()
    
    def save_violin_transparent(self):
        if not self.shared_info.results_dict:
            self.save_error_message("Error", "No data has been generated, please run phasor analysis first.")
            return

        output_dir = QFileDialog.getExistingDirectory(self.main_window, "Select the folder to save the violin plots")
        print(output_dir)
       
        if output_dir:
            # Prompt the user for the file name
            text, ok = QInputDialog.getText(self.main_window, "Save File", "Enter file name:", QLineEdit.Normal, "violin_plots")
            if ok and text:
                file_name = text
            else:
                return
            
            progress_dialog = QProgressDialog("Saving data...", "", 0, 0, self.main_window)
            progress_dialog.setWindowTitle("Saving Data")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setCancelButton(None)
            progress_dialog.show()

            # Process events to ensure the dialog is shown
            QApplication.processEvents()

            # Add a small delay to ensure the dialog displays correctly
            QTimer.singleShot(100, lambda: save_data.save_violin_plot(output_dir, progress_dialog, self.shared_info.config, self.shared_info.df_stats, file_name ))
            
        else:
            return

    def save_csv(self):
        if not self.shared_info.results_dict:
            self.save_error_message("Error", "No data has been generated, please run phasor analysis first.")
            return

        output_dir = QFileDialog.getExistingDirectory(self.main_window, "Select the folder to .csv file")
        print(output_dir)
        
        if output_dir:
            # Save the .csv filr
            save_data.save_df_csv(output_dir, self.shared_info.df_stats)
        else:
            return



class ConditionInputDialog(QDialog):
    # class for adding new conditions
    def __init__(self, previous_conditions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Experimental Condition")
        
        self.comboBox = QComboBox(self)
        self.comboBox.setEditable(True)
        self.comboBox.addItems(previous_conditions)
        
        layout = QVBoxLayout()
        layout.addWidget(self.comboBox)
        
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        
    def getCondition(self):
        return self.comboBox.currentText()

    