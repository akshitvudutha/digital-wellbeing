import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize

app = QApplication(sys.argv)
icon = QIcon('D:/Projects/Digital Wellbeing/assets/icons/app_icon.svg')
pixmap = icon.pixmap(QSize(256, 256))
pixmap.save('D:/Projects/Digital Wellbeing/website/public/favicon.ico', 'ICO')
