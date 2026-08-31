import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize

app = QApplication(sys.argv)
# Load SVG as icon to let Qt render it
icon = QIcon('D:/Projects/Digital Wellbeing/assets/icons/app_logo.svg')
# Get 256x256 pixmap
pixmap = icon.pixmap(QSize(256, 256))
pixmap.save('D:/Projects/Digital Wellbeing/website/public/favicon.ico', 'ICO')
