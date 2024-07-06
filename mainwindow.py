from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import Qt

from parameters_box import ParameterWidgets
from ui_layout import UILayout


class MainWindow(QMainWindow):
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("App")
        self.fixed_dpi = 110
        
        self.parameters_data = ParameterWidgets(self)
        # Initialize the UI layout
        self.ui_layout = UILayout(self)
        self.ui_layout.prepareLayout()