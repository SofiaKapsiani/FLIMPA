from PySide6.QtWidgets import (QMainWindow, QTableWidget, QSizePolicy)

from utils.toolbar import ToolBarComponents
from utils.ui_layout import UILayout
from utils.parameters_box import ParameterWidgets
from utils.phasor_plot import PhasorPlot

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar2QT


class MainWindow(QMainWindow):
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("App")
        self.fixed_dpi = 110

        # define phasor plot figure and canvas 
        self.figure_phasor = Figure(figsize=(6.5, 6), dpi=self.fixed_dpi, facecolor=(18/255, 18/255, 18/255))
        self.canvas_phasor = FigureCanvas(self.figure_phasor)

        # initialise intensity image shown on tab
        self.figure = Figure( figsize=(6, 6), dpi=self.fixed_dpi, facecolor=(18/255, 18/255, 18/255))
        self.canvas = FigureCanvas(self.figure)

        # initialise the table for displaying filenames
        self.file_names_table = QTableWidget()
        self.file_names_table.horizontalHeader().setStretchLastSection(True)
        self.file_names_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.parameters_data = ParameterWidgets(self) # fitting parameters
        self.phasor_componets = PhasorPlot(self) # phasor plot 

        # initialize the UI layout
        self.ui_layout = UILayout(self)
        # setup toolbar
        self.toolbar_components = ToolBarComponents(self, self.app)
        self.ui_layout.prepareLayout()

        
        