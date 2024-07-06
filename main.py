from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication
from dark_theme import get_darkModePalette 
import sys
import os

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Hello World")
        l = QtWidgets.QLabel("My simple app.")
        l.setMargin(10)
        self.setCentralWidget(l)
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=2'])
    app.setStyle( 'Fusion' )
    app.setPalette( get_darkModePalette( app ) )
    window = MainWindow()
    window.setWindowTitle("FLIMPA") 
    window.showMaximized()
    app.exec()