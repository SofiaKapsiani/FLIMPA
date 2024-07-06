from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication
from utils.dark_theme import get_darkModePalette 
from utils.mainwindow import MainWindow

import sys
import os

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

app = QApplication(sys.argv + ['-platform', 'windows:darkmode=2'])
app.setStyle( 'Fusion' )
app.setPalette( get_darkModePalette( app ) )
window = MainWindow(app)
window.setWindowTitle("FLIMPA") 
window.showMaximized()
app.exec()