import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from ui.widgets.flow_layout import FlowLayout
from PySide6.QtCore import QTimer

app = QApplication(sys.argv)

class TestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        
        self.container = QVBoxLayout()
        self.layout.addLayout(self.container)
        
        self.grid_container = QVBoxLayout()
        self.grid_content = QWidget()
        self.grid_layout = FlowLayout(self.grid_content)
        self.grid_container.addWidget(self.grid_content)
        
        self.grid_title = QLabel("Additional Insights")
        self.grid_container.insertWidget(0, self.grid_title)
        
        self.layout.addLayout(self.grid_container)
        
        self.build_count = 0
        self.build()
        
        QTimer.singleShot(1000, self.build)
        QTimer.singleShot(2000, self.build)
        QTimer.singleShot(3000, self.print_tree)
        
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def build(self):
        self._clear_layout(self.container)
        self._clear_layout(self.grid_layout)
        
        title = QLabel(f"Today's Breakdown {self.build_count}")
        self.container.addWidget(title)
        
        row = QHBoxLayout()
        row.addWidget(QLabel("Donut"))
        self.container.addLayout(row)
        
        c = QLabel(f"Card {self.build_count}")
        self.grid_layout.addWidget(c)
        
        self.build_count += 1
        
    def print_tree(self):
        print("--- Children of TestWidget ---")
        for c in self.findChildren(QLabel):
            print("Label:", c.text(), c.isVisible())
        app.quit()

w = TestWidget()
w.show()
sys.exit(app.exec())
