from PySide6.QtWidgets import (QMainWindow, QTableWidget, QSizePolicy,  QWidget, QVBoxLayout, QTableWidget, 
                               QScrollArea, QGridLayout)
from PySide6.QtCore import Qt
from utils.toolbar import ToolBarComponents
from utils.ui_layout import UILayout
from utils.parameters_box import ParameterWidgets
from utils.phasor_plot import PhasorPlot
from utils.plot_imgs import PlotImages
from utils.shared_data import SharedData
from utils.helper_functions import Helpers, NavigationToolbar_violin
from utils.settings_box import TabSettingsWidgets

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar2QT


class MainWindow(QMainWindow):
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("App")
        self.fixed_dpi = 110

        # initilise figures and canvas
        self.initialise_figures()

        # initialise the table for displaying filenames
        self.fileTable = QTableWidget()
        self.fileTable.horizontalHeader().setStretchLastSection(True)
        self.fileTable.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.parameters_data = ParameterWidgets(self) # fitting parameters
        self.phasor_componets = PhasorPlot(self) # phasor plot 
        self.plotImages = PlotImages(self) # plotting intensity and tau images
        self.helpers = Helpers(self) # import helper functions
        self.shared_info = SharedData()
        self.tab_settings = TabSettingsWidgets(self)

        # initialise the UI layout
        self.ui_layout = UILayout(self)
        # setup toolbar
        self.toolbar_components = ToolBarComponents(self, self.app)
        self.ui_layout.prepareLayout()

        # connect signals after everything is initialised
        self.connect_signals()

    def initialise_figures(self):
        '''initialise figures and canvas'''
        # define phasor plot figure and canvas 
        self.figure_phasor = Figure(figsize=(6.5, 6), dpi=self.fixed_dpi, facecolor=(18/255, 18/255, 18/255))
        self.canvas_phasor = FigureCanvas(self.figure_phasor)

        # initialise intensity image shown on tab
        self.figure = Figure( figsize=(6, 6), dpi=self.fixed_dpi, facecolor=(18/255, 18/255, 18/255))
        self.canvas = FigureCanvas(self.figure)

        # initialise lifetime image
        self.figure_tau = Figure(figsize=(6, 6), dpi=self.fixed_dpi,  facecolor=(18/255, 18/255, 18/255))
        self.canvas_tau = FigureCanvas(self.figure_tau)

        # initialise gallery image
        self.figure_gallery = Figure(figsize=(6, 6),  dpi=self.fixed_dpi, layout="compressed", facecolor=(18/255, 18/255, 18/255))
        self.canvas_gallery = FigureCanvas(self.figure_gallery)

        # initialise gallery intensity image
        self.figure_gallery_I = Figure(figsize=(6, 6),  dpi=self.fixed_dpi, layout="compressed", facecolor=(18/255, 18/255, 18/255))
        self.canvas_gallery_I = FigureCanvas(self.figure_gallery_I)
        
        # initialise violin plot image
        self.figure_violin = Figure(figsize=(6, 6), dpi=self.fixed_dpi, layout="compressed", facecolor=(18/255, 18/255, 18/255))
        self.canvas_violin = FigureCanvas(self.figure_violin)

    def connect_signals(self):
        '''connect signals'''
        self.fileTable.itemClicked.connect(self.plotImages.displaySelectedImage)
        self.fileTable.itemClicked.connect(self.helpers.displaySelectedtau)
        self.fileTable.itemChanged.connect(self.plotImages.handleCheckboxChange)
        self.ui_layout.tabs_widget.currentChanged.connect(self.onTabChanged)
    
    def analysis_finished(self):
        """Generate tabs with results once phasor plot analysis has finished running"""
        self.shared_info.config["selected_file"] = list(self.shared_info.results_dict.keys())[-1]
        self.tau_disp = self.shared_info.results_dict.get(self.shared_info.config["selected_file"])
        self.phasor_componets.plot_phasor_coordinates(cmap="gist_rainbow_r")

        # Check if the "Lifetime maps" tab already exists
        lifetime_maps_tab_index = None
        for i in range(self.ui_layout.tabs_widget.count()):
            if self.ui_layout.tabs_widget.tabText(i) == "Lifetime maps":
                lifetime_maps_tab_index = i
                break

        for i in range(self.ui_layout.tabs_widget.count()):
            if self.ui_layout.tabs_widget.tabText(i) == "Lifetime values":
                parameters_tab_index = i
                break

        if lifetime_maps_tab_index is not None:
            self.plotImages.plot_tau_map()
            self.phasor_componets.plot_phasor_coordinates(cmap="gist_rainbow_r")
            # If the "Parameters" tab already exists, update the table widget
            self.table_widget = self.ui_layout.tabs_widget.widget(parameters_tab_index).layout().itemAt(0).widget()
            self.helpers.update_table_widget()
            self.helpers.resizeGallery()
            self.helpers.resizeGallery_I()
            self.helpers.resizeViolin()
        else:
            """Output parameters tab"""
            tab_tau_table = QWidget()
            tab_tau_table.setStyleSheet("QWidget { background-color: rgb(18, 18, 18); }")
            self.layout_tau_table = QVBoxLayout()
            tab_tau_table.setLayout(self.layout_tau_table)
            self.ui_layout.tabs_widget.addTab(tab_tau_table, "Lifetime values")

            # Create a QTableWidget to display the DataFrame contents
            self.table_widget = QTableWidget()
            self.layout_tau_table.addWidget(self.table_widget)
            self.layout_tau_table.addLayout(self.tab_settings.input_layout(box_type='table_box'))
            self.helpers.update_table_widget()

            """Lifetime maps tab"""
            tab_tau_maps = QWidget()
            tab_tau_maps.setStyleSheet("QWidget { background-color: rgb(18, 18, 18);  }")
            self.layout_tau_maps = QVBoxLayout()
            self.layout_tau_maps.addWidget(self.canvas_tau)
            self.layout_tau_maps.addLayout(self.tab_settings.input_layout(box_type='lifetime_box'))
            tab_tau_maps.setLayout(self.layout_tau_maps)

            self.plotImages.plot_tau_map()
            self.ui_layout.tabs_widget.addTab(tab_tau_maps, "Lifetime maps")

            """Gallery (tau) tab"""
            gallery_widget = QWidget()
            gallery_widget.setStyleSheet("QWidget { background-color: rgb(18, 18, 18); }")
            self.gallery_layout_V = QVBoxLayout()
            self.scroll_area = QScrollArea()  # Initialize scroll area
            self.scroll_area.setWidgetResizable(True)  # Allow content resizing within scroll area

            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            self.gallery_container = QWidget()
            self.gallery_layout_grid = QGridLayout(self.gallery_container)
            self.gallery_layout_grid.setAlignment(Qt.AlignCenter)  # Center the grid layout
            self.scroll_area.setWidget(self.gallery_container)

            self.gallery_layout_V.addWidget(self.scroll_area)
            self.gallery_layout_V.addLayout(self.tab_settings.input_layout(box_type='gallery_box'))

            gallery_widget.setLayout(self.gallery_layout_V)
            self.ui_layout.tabs_widget.addTab(gallery_widget, "Gallery (tau)")

            """Gallery (I) tab"""
            gallery_widget_I = QWidget()
            gallery_widget_I.setStyleSheet("QWidget { background-color: rgb(18, 18, 18); }")
            self.gallery_layout_V_I = QVBoxLayout()
            self.scroll_area_I = QScrollArea()  # Initialize scroll area
            self.scroll_area_I.setWidgetResizable(True)  # Allow content resizing within scroll area

            self.scroll_area_I.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scroll_area_I.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            self.gallery_container_I = QWidget()
            self.gallery_layout_grid_I = QGridLayout(self.gallery_container_I)
            self.scroll_area_I.setWidget(self.gallery_container_I)

            self.gallery_layout_V_I.addWidget(self.scroll_area_I)
            self.gallery_layout_V_I.addLayout(self.tab_settings.input_layout(box_type='input_box'))

            gallery_widget_I.setLayout(self.gallery_layout_V_I)
            self.ui_layout.tabs_widget.addTab(gallery_widget_I, "Gallery (I)")

            """Violin plots tab"""
            violin_plot_tab = QWidget()
            violin_plot_tab.setStyleSheet("QWidget { background-color: rgb(18, 18, 18); }")
            self.violin_plot_layout = QVBoxLayout()

            self.toolbar_violin = NavigationToolbar_violin(self.canvas_violin, self)
            self.violin_plot_layout.addWidget(self.toolbar_violin)
            self.violin_plot_layout.addWidget(self.canvas_violin)
            self.violin_plot_layout.addLayout(self.tab_settings.input_layout(box_type='violin_box'))

            violin_plot_tab.setLayout(self.violin_plot_layout)
            self.ui_layout.tabs_widget.addTab(violin_plot_tab, "Violin plots")
    
    def onTabChanged(self, index):
        # Save the name of the active tab
        current_tab_name = self.ui_layout.tabs_widget.tabText(index)
        
        if self.ui_layout.tabs_widget.tabText(index) == "Intensity display":
            if self.shared_info.config["selected_file"] in self.shared_info.intensity_img_dict:
                self.plotImages.plot_img()

        elif self.ui_layout.tabs_widget.tabText(index) == "Lifetime maps":
            self.plotImages.plot_tau_map()
            self.phasor_componets.plot_phasor_coordinates(cmap="gist_rainbow_r")
            self.shared_info.last_active_tab = current_tab_name

        elif self.ui_layout.tabs_widget.tabText(index) == "Gallery (tau)":
            #print(f"Plot type updated to: {self.shared_info.phasor_settings['plot_type']}")
            if self.shared_info.phasor_settings["plot_type"] == "individual":
                self.phasor_componets.plot_phasor_gallery_individual(data_dict=self.shared_info.results_dict)
            elif self.shared_info.phasor_settings["plot_type"] == "condition":
                self.phasor_componets.plot_phasor_gallery_condition(data_dict=self.shared_info.results_dict)
            self.helpers.resizeGallery()
            self.shared_info.last_active_tab = current_tab_name

        elif self.ui_layout.tabs_widget.tabText(index) == "Gallery (I)":
            self.helpers.resizeGallery_I()

        elif self.ui_layout.tabs_widget.tabText(index) == "Violin plots":
            self.helpers.resizeViolin()

    def resizeEvent(self, event):
        """resize figures if window size has been changed"""
        super().resizeEvent(event)
    
        try:
            currentIndex = self.ui_layout.tabs_widget.currentIndex()
            if self.ui_layout.tabs_widget.tabText(currentIndex) == "Intensity display":
                self.helpers.resizeIntensity()
            elif self.ui_layout.tabs_widget.tabText(currentIndex) == "Lifetime maps":
                self.helpers.resizeTau()
            elif self.ui_layout.tabs_widget.tabText(currentIndex) == "Gallery (tau)":
                self.helpers.resizeGallery()
            elif self.ui_layout.tabs_widget.tabText(currentIndex) == "Gallery (I)":
                self.helpers.resizeGallery_I()
            elif self.ui_layout.tabs_widget.tabText(currentIndex) == "Violin plots":
                self.helpers.resizeViolin()
        except Exception as e:
            print(f"Error in resizeEvent: {e}")
    
    