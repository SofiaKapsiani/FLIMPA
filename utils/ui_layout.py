from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
                                QTableWidget, QWidget, QTabWidget, QSizePolicy, QScrollArea)


"""File for providing the UI layout"""

class UILayout:
    def __init__(self, main_window):
        self.main_window = main_window

    def prepareLayout(self):

        """Preparing left-hand layout"""
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

        """Preparing right-hand layout"""
        # Tabs for displaying images
        tabs_visualise_imgs = QWidget()
        tabs_visualise_imgs.setStyleSheet("QWidget { background-color: rgb(18, 18, 18); }")
        layout_tabs = QVBoxLayout()
        layout_tabs.addWidget(self.main_window.canvas) # add figure for displaying intensity image
        tabs_visualise_imgs.setLayout(layout_tabs)
        
        # initate tabs widget and define style
        self.tabs_widget = QTabWidget()
        self.tabs_widget.addTab(tabs_visualise_imgs, "Intensity display")
        self.tabs_widget.setStyleSheet("""
            QTabWidget::pane { /* The tab widget frame */
                border: 1px solid rgb(18, 18, 18);}
            QTabBar::tab {
                    background: rgb(40, 40, 40);
                    color: white; 
                    border: 8px solid rgb(40, 40, 40);
                    margin-right: 1px}
            QTabBar::tab:selected {
                color: rgb(60, 162, 161);}""")
        self.tabs_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        # table to show file names
        table_filenames = QVBoxLayout()
        self.main_window.file_names_table.setStyleSheet("""QTableWidget {
                background-color: rgb(40, 40, 40);
                margin-top:50 px;
                border: 1px solid rgb(40, 40, 40);                       
                padding: 10px;                         
                }
                """)
        table_filenames.addWidget(self.main_window.file_names_table, 14)
        

        # button to delete imported files not needed for the analysis
        delete_files_button = QPushButton("Delete selected files")
        delete_files_button.setStyleSheet('QPushButton {color: white}')
        delete_files_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        #delete_files_button.clicked.connect(self.delete_selected_files)

        # create a vertical layout for the delete button to center it
        delete_v_layout = QVBoxLayout()
        delete_v_layout.addStretch(1)
        delete_v_layout.addWidget(delete_files_button)
        delete_v_layout.addStretch(1)
        # add delete button under filenames table
        table_filenames.addLayout(delete_v_layout, 1)
        table_filenames.setSpacing(10)


        # Horizontal layout for displaying the tabs and table with filenames
        right_h_widget = QWidget()
        h_right_hand = QHBoxLayout()
        h_right_hand.addWidget(self.tabs_widget, 5)
        h_right_hand.addLayout(table_filenames, 2)  # add the fileTable here
        h_right_hand.setSpacing(10)
        right_h_widget.setLayout(h_right_hand)

        # adjust height position of right-hand side layout
        right_side_layout = QVBoxLayout()
        right_side_layout.addStretch(1)
        right_side_layout.addWidget(right_h_widget)
        right_side_layout.addStretch(1)

        # main layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_side_layout, 1)
        main_layout.addLayout(right_side_layout, 1)

        # central widget for displaying layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.main_window.setCentralWidget(central_widget)
