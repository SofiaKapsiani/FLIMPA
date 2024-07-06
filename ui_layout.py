from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QTableWidget, QWidget, QTabWidget, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt

"""File for providing the initial UI layout"""

class UILayout:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tabWidget = QTabWidget()

    def prepareLayout(self):
        # Initialize the parameters group box
        parameters_group_box = QGroupBox("") # no title
        parameters_group_box.setLayout(self.main_window.parameters_data.create_parameters_layout())
        parameters_group_box.setStyleSheet("""QGroupBox {
                background-color: rgb(40, 40, 40);
                margin-top:15 px;
                border: 1px solid rgb(40, 40, 40);
                border-radius: 4px;                           
                padding: 10px;                         
                }""")

        # use an additional horizontal layout to center the parameters group box
        h_layout_parameters = QHBoxLayout()
        h_layout_parameters.addStretch(1)
        h_layout_parameters.addWidget(parameters_group_box)  # Add the vertical layout containing the label and group box
        h_layout_parameters.addStretch(1)

        # central widget for displaying layout
        central_widget = QWidget()
        central_widget.setLayout(h_layout_parameters)
        self.main_window.setCentralWidget(central_widget)
