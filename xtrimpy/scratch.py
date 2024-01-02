import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class XtrimGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.last_x, self.last_y = None, None
        self.initUI()

        QApplication.instance().installEventFilter(self)

    def initUI(self):
        main_layout = QVBoxLayout(self)
        self.setWindowTitle('XTRIM')
        self.setGeometry(100, 100, 1000, 710)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        main_layout.addWidget(self.canvas)

        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.show()

    def on_hover(self, event):
        if event.inaxes:
            self.last_x, self.last_y = event.xdata, event.ydata

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_A:
                print("A key pressed (Global Handler)")
        return super().eventFilter(source, event)

def main():
    app = QApplication(sys.argv)
    ex = XtrimGUI()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
