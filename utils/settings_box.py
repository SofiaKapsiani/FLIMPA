from PySide6.QtWidgets import QLabel, QHBoxLayout, QLineEdit, QGroupBox, QGridLayout, QSizePolicy, QVBoxLayout, QWidget, QComboBox
from PySide6.QtCore import Qt

from utils.shared_data import SharedData

class TabSettingsWidgets():
    """Visualisation settings for tabs"""
    def __init__(self, main_window):
        self.shared_info = SharedData()
        self.main_window = main_window
        self.widget_dict = {}  # Dictionary to store references to widgets by param_id
        self.helpers = self.main_window.helpers # import helper functions

    def input_parameters(self, param_name, input_type="lineedit", param_id="", items=[], plot_type=None):
        label = QLabel(str(param_name))
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if plot_type != None:
            if plot_type  == "tau_map":
                plot_id = "tau"
            else:
                plot_id = plot_type
            unique_param_id = f"{plot_id}_{param_id}" if plot_type else param_id

        h_layout_parameters = QHBoxLayout()
        h_layout_parameters.addWidget(label)

        if input_type == "lineedit":
            input_widget = QLineEdit()
            input_widget.setFixedWidth(80)
            input_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            input_widget.setAlignment(Qt.AlignCenter)
            input_widget.setText(str(self.shared_info.config.get(param_id)))
            input_widget.editingFinished.connect(self.update_img(input_type, input_widget, param_id, plot_type))
            input_widget.setStyleSheet("""QLineEdit { 
                                        background-color: rgb(63, 63, 63);
                                        color: white; }""")
            h_layout_parameters.addWidget(input_widget)
            if plot_type != None:
                self.widget_dict[unique_param_id] = input_widget  # Store widget reference

        elif input_type == "combobox":
            input_widget = QComboBox()
            input_widget.addItems(items)
            input_widget.setFixedWidth(80)
            input_widget.setEditable(True)  # Set editable to False
            input_widget.lineEdit().setAlignment(Qt.AlignCenter)
            input_widget.currentIndexChanged.connect(self.update_img(input_type, input_widget, param_id, plot_type))
            input_widget.setStyleSheet("""QComboBox { 
                                       background-color: rgb(63, 63, 63);
                                       color: white; }""")
            h_layout_parameters.addWidget(input_widget)
            if plot_type != None:
                self.widget_dict[unique_param_id] = input_widget  # Store widget reference

        return h_layout_parameters
    
    def table_settings_input(self, param_name, items=[]):
        label = QLabel(str(param_name))
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        h_layout_parameters = QHBoxLayout()
        h_layout_parameters.addWidget(label)

        input_widget = QComboBox()
        input_widget.addItems(items)
        input_widget.setFixedWidth(80)
        input_widget.setEditable(False)
        #input_widget.lineEdit().setAlignment(Qt.AlignCenter)
        input_widget.currentIndexChanged.connect(self.helpers.update_table_widget)  # Trigger update_table_widget on change
        input_widget.setStyleSheet("""QComboBox { 
                                    background-color: rgb(63, 63, 63);
                                    color: white; }""")
        h_layout_parameters.addWidget(input_widget)

        self.widget_dict["table_Group by"] = input_widget  # Store widget reference

        return h_layout_parameters

    
    def update_img(self, input_type, input_widget, param_id, plot_type):
        def action_wrapper():
            if input_type == "lineedit":
                text = input_widget.text()
            elif input_type == "combobox":
                text = input_widget.currentText()
            
            self.update_parameters(param_id, text, plot_type)
            self.sync_widgets(param_id, text)
            
        return action_wrapper
    
    def sync_widgets(self, param_id, text):
        # Loop through all widgets and update those with matching param_id
        for key, widget in self.widget_dict.items():
            key_split = key.split("_")
            key_id = key_split[-2] + "_" + key_split[-1]
    
            if key_id == param_id:  # Adjust condition to match the partial param_id
                current_text = widget.text() if isinstance(widget, QLineEdit) else widget.currentText()
                if current_text != text:
                    widget.blockSignals(True)
                    if isinstance(widget, QLineEdit):
                        widget.setText(text)
                    elif isinstance(widget, QComboBox):
                        widget.setCurrentText(text)
                    widget.blockSignals(False)

    def update_parameters(self, param_id, text, plot_type):
        # update images based on parameteres inputed
        self.shared_info.config[param_id] = text
       
        if self.shared_info.config["selected_file"] == None:
            filename = list(self.shared_info.raw_data_dict.keys())[-1]
        else:
            filename = self.shared_info.config["selected_file"]

        if filename in self.shared_info.intensity_img_dict:
            if param_id.split("_")[1] == "int":
                self.main_window.plotImages.gallery_imgs_I(data_dict=self.shared_info.results_dict)
            elif param_id.split("_")[0] == "lifetime":
                # update "lifetime maps" tab
                if plot_type == "tau_map":
                    self.main_window.plotImages.plot_tau_map()
                    if param_id != "lifetime_itegrate":
                        self.main_window.phasor_componets.plot_phasor_coordinates(cmap="gist_rainbow_r")
                        
                # update "gallery" tab
                elif plot_type == "gallery":
                    self.main_window.plotImages.gallery_imgs(data_dict=self.shared_info.results_dict)
            # update violin plots
            elif param_id == "tau_violin":
                self.main_window.plotImages.violin_plots()
                
                    
            

    def input_box(self):
        grid_parameters = QGridLayout()
        grid_parameters.setHorizontalSpacing(6)
        grid_parameters.setVerticalSpacing(6)

        # Adding parameter inputs to the grid
        grid_parameters.addLayout(self.input_parameters(param_name="Min. intensity", param_id="vmin_int"), 0, 0)
        grid_parameters.addLayout(self.input_parameters(param_name="Max. intensity", param_id="vmax_int" ), 0, 1)
    
        return grid_parameters
    
    def lifetime_box(self):
        grid_parameters = QGridLayout()
        grid_parameters.setHorizontalSpacing(6)
        grid_parameters.setVerticalSpacing(6)

        # Adding parameter inputs to the grid
        grid_parameters.addLayout(self.input_parameters(param_name="Min. lifetime (ns)", param_id="lifetime_vmin", plot_type = "tau_map"), 0, 0)
        grid_parameters.addLayout(self.input_parameters(param_name="Max. lifetime (ns)", param_id="lifetime_vmax", plot_type = "tau_map"), 0, 1)
        grid_parameters.addLayout(self.input_parameters(param_name="Lifetime map", input_type="combobox", items=["average", "M", "phi"], param_id="lifetime_map", plot_type = "tau_map"), 1, 0)
        grid_parameters.addLayout(self.input_parameters(param_name="Integrate itensity", input_type="combobox", items=["False", "True"], param_id="lifetime_itegrate", plot_type = "tau_map"), 1, 1)
        
    
        return grid_parameters
    
    def gallery_box(self):
        grid_parameters = QGridLayout()
        grid_parameters.setHorizontalSpacing(6)
        grid_parameters.setVerticalSpacing(6)

        # Adding parameter inputs to the grid
        grid_parameters.addLayout(self.input_parameters(param_name="Min. lifetime (ns)", param_id="lifetime_vmin", plot_type = "gallery"), 0, 0)
        grid_parameters.addLayout(self.input_parameters(param_name="Max. lifetime (ns)", param_id="lifetime_vmax", plot_type = "gallery"), 0, 1)
        grid_parameters.addLayout(self.input_parameters(param_name="Lifetime map", input_type="combobox", items=["average", "M", "phi"], param_id="lifetime_map", plot_type = "gallery"), 1, 0)
        grid_parameters.addLayout(self.input_parameters(param_name="Integrate itensity", input_type="combobox", items=["False", "True"], param_id="lifetime_itegrate", plot_type = "gallery"), 1, 1)
        #grid_parameters.addLayout(self.input_parameters(param_name="Columns"), 0, 2)
    
        return grid_parameters
    
    def violin_box(self):
        grid_parameters = QGridLayout()
        grid_parameters.setHorizontalSpacing(6)
        grid_parameters.setVerticalSpacing(6)

        # Adding parameter inputs to the grid
        grid_parameters.addLayout(self.input_parameters(param_name="Lifetime map", input_type="combobox", items=["average", "M", "phi"], param_id="tau_violin", plot_type = "violin"), 0, 0)
    
        return grid_parameters
    
    def table_box(self):
        grid_parameters = QGridLayout()
        grid_parameters.setHorizontalSpacing(6)
        grid_parameters.setVerticalSpacing(6)

        grid_parameters.addLayout(self.table_settings_input(param_name="Group by", 
                                                        items=["None", "Condition", "Sample"]), 0, 0)
    
        return grid_parameters
    
    def input_layout(self, box_type):
        # group setting box and format
        input_group_box = QGroupBox("Settings")
        
        if box_type == 'input_box':
            input_group_box.setLayout(self.input_box())
        elif box_type == 'lifetime_box':
            input_group_box.setLayout(self.lifetime_box())
        elif box_type == 'gallery_box':
            input_group_box.setLayout(self.gallery_box())
        elif box_type == 'violin_box':
            input_group_box.setLayout(self.violin_box())
        elif box_type == 'table_box':
            input_group_box.setLayout(self.table_box())
        
        input_group_box.setStyleSheet("""
            QGroupBox {
                background-color: rgb(18, 18, 18);
                border: 1px solid rgb(40, 40, 40);
                border-radius: 4px;
                margin-top:10 px;                                               
                padding: 10px;                         
                }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center; /* Align the title at the top center */
                padding: 0 2px;
                color: rgb(255, 255, 255); /* Example text color */
            }""")
        
        # Layout for the title label and parameters group box
        v_input_layout = QVBoxLayout()
        v_input_layout.addWidget(input_group_box)  # Add the parameters group box below the label
        
        # horizontal layout to center box
        h_tab_settings = QHBoxLayout()
        h_tab_settings.addStretch(1)
        h_tab_settings.addLayout(v_input_layout) 
        h_tab_settings.addStretch(1)
    
        return h_tab_settings

