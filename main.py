import sys
import os
from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from utils.dark_theme import get_darkModePalette
from utils.mainwindow import MainWindow

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# Ensure the icon path is correct
base_path = os.path.abspath(os.path.dirname(__file__))
icon_path = os.path.join(base_path, 'icon', 'icon_f.ico')

app = QApplication(sys.argv + ['-platform', 'windows:darkmode=2'])
app.setStyle('Fusion')
app.setPalette(get_darkModePalette(app))

# Load the icon and resize it to a smaller size
icon = QIcon(QPixmap(icon_path))
app.setWindowIcon(icon)

window = MainWindow(app)
window.setWindowTitle("FLIMPA (v1.3.4)")
window.setWindowIcon(icon)  # Set the window icon here
window.showMaximized()

app.exec()
