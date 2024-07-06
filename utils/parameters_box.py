from PySide6.QtWidgets import QLabel, QHBoxLayout, QLineEdit, QComboBox, QGridLayout, QSizePolicy, QApplication, QWidget
from PySide6.QtCore import Qt

from utils.mainwindow import *
from utils.shared_data import SharedData 

class ParameterWidgets():
    def __init__(self, main_window):
        self.main_window = main_window
        self.ref_file_combobox = None  # Specific reference for the "Reference file" combobox
        self.shared_info = SharedData()
        

    def parameter_input(self, param_name, input_type="lineedit", param_id="", items=[]):
        
        label = QLabel(str(param_name))
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        h_layout_parameters = QHBoxLayout()
        h_layout_parameters.addWidget(label)

        if input_type == "lineedit":
            input_widget = QLineEdit()
            input_widget.setFixedWidth(80)
            input_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            input_widget.setAlignment(Qt.AlignCenter)
            #set default text
            input_widget.setText(str(self.shared_info.config.get(str(param_id), ""))) 
            input_widget.editingFinished.connect(self.combined_actions(input_type,input_widget, param_id))
            input_widget.setStyleSheet("""QLineEdit { 
                                       background-color: rgb(63, 63, 63);
                                       color: white; }""")
            h_layout_parameters.addWidget(input_widget)
            

        elif input_type == "combobox":
            input_widget = QComboBox()
            input_widget.addItems(items)
            input_widget.setFixedWidth(80)
            input_widget.setEditable(True)
            input_widget.lineEdit().setAlignment(Qt.AlignCenter)
            input_widget.currentIndexChanged.connect(self.combined_actions(input_type,input_widget, param_id))
            if param_id == "ref_file":  # Store reference to "Reference file" combobox
                self.ref_file_combobox = input_widget
            input_widget.setStyleSheet("""QComboBox { 
                                       background-color: rgb(63, 63, 63);
                                       color: white; }""")
            h_layout_parameters.addWidget(input_widget)

        return h_layout_parameters



    def combined_actions(self, input_type,input_widget, param_id):
        def action_wrapper():
            if input_type == "lineedit":
                text = input_widget.text()
            elif input_type == "combobox":
                text = input_widget.currentText()
            self.update_parameters(param_id, text)
        return action_wrapper  # Return the wrapper function to be connected as a slot.


    def update_parameters(self, param_id, text):
        self.shared_info.config[param_id] = text
        if param_id == "min_photons":
            self.main_window.plotImages.update_mask_for_current_image()  # Call update_mask_for_current_image when min_photons is updated
        elif param_id == "max_photons":
            self.main_window.plotImages.update_mask_for_current_image()  # Call update_mask_for_current_image when min_photons is updated

    
    def update_ref_file(self, ref_filenames):
        if self.ref_file_combobox:
            self.ref_file_combobox.clear()
            self.ref_file_combobox.addItems(ref_filenames)
            print("Updated reference files:", ref_filenames)


    def create_parameters_layout(self):
        grid_parameters = QGridLayout()
        grid_parameters.setHorizontalSpacing(6)
        grid_parameters.setVerticalSpacing(6)

        # Adding parameter inputs to the grid
        grid_parameters.addLayout(self.parameter_input(param_name="Frequency (MHz)", param_id="frequency"), 0, 0)
        grid_parameters.addLayout(self.parameter_input(param_name="Min. photon counts", param_id="min_photons", ), 0, 1)
        grid_parameters.addLayout(self.parameter_input(param_name="Max. photon counts", param_id="max_photons"), 1, 1)
        grid_parameters.addLayout(self.parameter_input(param_name="Reference file", input_type="combobox", items=["None"], param_id="ref_file"), 1, 0)
        grid_parameters.addLayout(self.parameter_input(param_name="Reference lifetime (ns)", param_id="ref_lifetime"), 2, 0)
        grid_parameters.addLayout(self.parameter_input(param_name="Number of bins", input_type="combobox", items=["3x3", "7x7", "9x9", "None"], param_id="bins"), 2, 1)

        return grid_parameters