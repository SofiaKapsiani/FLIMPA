from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
                                QTableWidget, QWidget, QTabWidget, QSizePolicy, QScrollArea)


"""File for providing the UI layout"""

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

        # create the "Run Phasor Plot" button with adjusted size
        runPhasorPlotButton = QPushButton("Run Phasor Plot Analysis")
        runPhasorPlotButton.setStyleSheet('QPushButton {color: white}')
        runPhasorPlotButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        #runPhasorPlotButton.clicked.connect(self.run_phasor)

        # create a horizontal layout for the run button to center it
        buttonHLayout = QHBoxLayout()
        buttonHLayout.addStretch(2)
        buttonHLayout.addWidget(runPhasorPlotButton)
        buttonHLayout.addStretch(2)

        # add to vertical layout to ensure that the phasor button does stretch with larger screens
        buttonVLayout = QVBoxLayout()
        buttonVLayout.addStretch(1)
        buttonVLayout.addLayout(buttonHLayout)
        buttonVLayout.addStretch(1)

        # horizontal layout to for phasor plot visualisation
        h_layout_phasors = QHBoxLayout()
        h_layout_phasors.addStretch(1)
        self.main_window.phasor_componets.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        h_layout_phasors.addWidget(self.main_window.phasor_componets)
        h_layout_phasors.addStretch(1)

        # main left-hand side layout combining parameters and phasor plots
        left_side_layout = QVBoxLayout()
        left_side_layout.addLayout(h_layout_parameters, 2)
        left_side_layout.addLayout(buttonVLayout, 1)
        left_side_layout.addLayout(h_layout_phasors, 9)

        # central widget for displaying layout
        central_widget = QWidget()
        central_widget.setLayout(left_side_layout)
        self.main_window.setCentralWidget(central_widget)
