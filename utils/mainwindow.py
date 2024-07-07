from PySide6.QtWidgets import (QMainWindow, QTableWidget, QSizePolicy)

from utils.toolbar import ToolBarComponents
from utils.ui_layout import UILayout
from utils.parameters_box import ParameterWidgets
from utils.phasor_plot import PhasorPlot
from utils.plot_imgs import PlotImages
from utils.shared_data import SharedData
from utils.helper_functions import Helpers

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

        # initialize the UI layout
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
        #self.ui_layout.tabs_widget.currentChanged.connect(self.onTabChanged)

    
    