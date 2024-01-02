import sys
import os
import argparse
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, \
    QMenuBar, QAction, QStatusBar, QFileDialog, QTableWidget, QTableWidgetItem, \
    QDialog, QTextEdit, QSizePolicy, QTextBrowser
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtCore import Qt, QEvent, pyqtSignal, QObject
import logging
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import pkg_resources


import WaveSpec.wavespec
from utils import *

def parser_init():
    """Create command-line argument parser for this script."""
    parser = argparse.ArgumentParser(description="Xtrim GUI")
    parser.add_argument(
        'filenames',
        type=str,
        help='Spectrum to be displayed',
        default=None,
        nargs='*'
        )
    return parser

class StatusBarHandler(logging.Handler, QObject):
    newLogRecord = pyqtSignal(str)

    def __init__(self, statusBar):
        super().__init__()
        QObject.__init__(self)
        self.log_records = []
        self.statusBar = statusBar

    def emit(self, record):
        log_entry = self.format(record)
        self.log_records.append(log_entry)
        self.statusBar.showMessage(log_entry)
        self.newLogRecord.emit(log_entry)  # Emit the new log record


class XtrimGUI(QWidget):
    def __init__(self, filenames=None):
        super().__init__()

        self.package = __name__.split('.')[0]

        self.specs = []
        self.last_x, self.last_y = np.nan, np.nan

        self.input_mode = False
        self.input_buffer = []

        # statusbar message
        self.default_message = "Ready - 'a': zoom box; 'b': reset y=0; 'c': reset plot"

        # plotting keywords
        self.plotting = {
            "box": [None, None, None, None],
            #"initial_box": [None, None, None, None], 
            "redshift": 0.,
            "ew_cont": [None, None, None, None],
            "ew": [np.nan, np.nan],
            "flux": [np.nan, np.nan],
            "gauss_lim": [None, None],
            "gauss_center": [np.nan, np.nan],
            "trim_lines": [],
            "redshift_line": np.nan,
            "blocking": None    # operation in progress, blocking other key events
        }

        # gauss model
        self.gauss_wave = None
        self.gauss_model = None

        # line list
        self.linelist = {
            "waves": [],
            "labels": [], 
            "kwargs": []
        }
        self.lldefaults = {
            "ls": '--',
            "color": 'lightblue'
        }

        self.initUI(filenames)
        self.setupLogging()
        QApplication.instance().installEventFilter(self)

        return

    def initUI(self, filenames):
        # logging box init
        self.logtext = None

        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setWindowTitle('XTRIM')
        self.setGeometry(100, 100, 1000, 710)

        path_to_icon = pkg_resources.resource_filename(self.package, 'lib/xtrim_icon.png')
        self.setWindowIcon(QIcon(path_to_icon))

        # Base 1
        base_1 = QVBoxLayout()
        main_layout.addLayout(base_1, 3)

        # Menu Bar
        menuBar = QMenuBar(self)
        main_layout.setMenuBar(menuBar)

        # File menu
        fileMenu = menuBar.addMenu('File')
        openAction = QAction('Open', self)
        openAction.triggered.connect(self.openFileNameDialog)
        fileMenu.addAction(openAction)
        saveAction = QAction('Save Workspace', self)
        fileMenu.addAction(saveAction)

        # help menu
        logMenu = menuBar.addMenu('Log')
        viewlogsAction = QAction('View Logs', self)
        viewlogsAction.triggered.connect(self.showLogDialog)
        logMenu.addAction(viewlogsAction)


        # help menu
        helpMenu = menuBar.addMenu('Help')
        helpAction = QAction('Help', self)
        helpAction.triggered.connect(self.showHelpDialog)
        helpMenu.addAction(helpAction)
        #redoAction = QAction('Redo', self)
        #editMenu.addAction(redoAction)

        # Title label
        #label_title = QLabel('File name')
        #base_1.addWidget(label_title)

        # Drawing area
        #draw_area = QFrame()
        #draw_area.setFrameShape(QFrame.StyledPanel)
        #draw_area.setFixedSize(850, 370)
        #base_1.addWidget(draw_area)
        # Drawing area with Matplotlib figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.StrongFocus)  # Set focus policy to accept focus
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.figure.add_subplot(111)
        base_1.addWidget(self.canvas)

        # x, y monitor
        self.label_xy = QLabel('(x, y) = {0:.4f}, {1:.4f}'.format(self.last_x, self.last_y))
        base_1.addWidget(self.label_xy)

        # Base 1 Bottom Controls
        #base_1_bottom = QHBoxLayout()
        #base_1.addLayout(base_1_bottom)

        # Text controls at the bottom
        #text_xr1 = QLineEdit()
        #text_xr2 = QLineEdit()
        #text_smooth = QLineEdit()
        #base_1_bottom.addWidget(text_xr1)
        #base_1_bottom.addWidget(text_xr2)
        #base_1_bottom.addWidget(QLabel('Smooth:'))
        #base_1_bottom.addWidget(text_smooth)



        # Base 2
        base_2 = QHBoxLayout()
        main_layout.addLayout(base_2, 1)

        # Buttons in Base 2
        base_21 = QVBoxLayout()
        label_values = QLabel('Values:')
        self.vtableWidget = QTableWidget()
        self.vtableWidget.setRowCount(0)  # Set number of rows
        self.vtableWidget.setColumnCount(3)  # Set number of columns
        # Column headers (optional)
        self.vtableWidget.setHorizontalHeaderLabels(["Quantity", "Value", "Error"])
        self.refresh_value_table()
        #self.vtableWidget.itemChanged.connect(self.ValueTableItemChanged)
        # TODO: Implement the above

        base_21.addWidget(label_values)
        base_21.addWidget(self.vtableWidget)
        base_2.addLayout(base_21, 1)

        # Reference list in Base 2
        base_22 = QVBoxLayout()
        label_files = QLabel('Loaded Files:')
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(0)  # Set number of rows
        self.tableWidget.setColumnCount(6)  # Set number of columns
        # Column headers (optional)
        self.tableWidget.setHorizontalHeaderLabels(["Filename", "+Redshift", "Smooth", "x", "+", "Color"])
        self.tableWidget.setColumnWidth(0, 200)
        self.tableWidget.setColumnWidth(1, 100)
        self.tableWidget.setColumnWidth(2, 70)
        self.tableWidget.setColumnWidth(3, 70)
        self.tableWidget.setColumnWidth(4, 70)
        self.tableWidget.setColumnWidth(5, 70)
        self.tableWidget.itemChanged.connect(self.TableItemChanged)
    
        
        base_22.addWidget(label_files)
        base_22.addWidget(self.tableWidget)
        base_2.addLayout(base_22, 2)

        self.statusBar = QStatusBar()
        main_layout.addWidget(self.statusBar)
        self.statusBar.showMessage(self.default_message)


        # Rest of Base 2
        # Add additional elements here as needed
        if filenames is not None:
            self.loadspec(filenames)
            path_to_linelist = pkg_resources.resource_filename(self.package, 'lib/line_list.dat')
            self.loadlinelist(path_to_linelist)
            self.update_color()
            self.plotspec(reset_lim=True)
            self.refresh_file_table()

        # Connect the hover event
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas.mpl_connect('key_press_event', self.keyPressEvent)

        # Show the window
        self.show()

    def setupLogging(self):
        # Configure logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Create custom handler
        self.handler = StatusBarHandler(self.statusBar)
        self.handler.setLevel(logging.INFO)

        # Create formatter and add it to the handler
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(self.handler)

        # Assign the logger to the class
        self.logger = logger
        return
    
    def showLogDialog(self):
        # Create the dialog if it doesn't exist or is not visible
        if not hasattr(self, 'dialog') or not self.dialog.isVisible():
            # Dialog for displaying logs
            self.dialog = QDialog(self)
            self.dialog.setWindowTitle("XTRIM Logs")

            self.dialog.resize(600, 400)
            layout = QVBoxLayout()

            # Text area for logs
            self.logtext = QTextEdit(self.dialog)
            self.logtext.setReadOnly(True)
            self.logtext.setText("\n".join(self.handler.log_records))  # Join log records and set as text
            layout.addWidget(self.logtext)

            self.dialog.setLayout(layout)
            #self.dialog.setWindowModality(Qt.WindowModal)
            
            # Connect the newLogRecord signal to update the log text edit
            self.handler.newLogRecord.connect(self.updateLogText)
        
            self.dialog.show()  # Show the dialog

        return

    def updateLogText(self, message):
        # Append the new message to the log text edit
        self.logtext.append(message)

        return

    def checkblocking(self, key):
        if self.plotting['blocking'] is None:
            return True
        elif self.plotting['blocking'] == key:
            return True
        else:
            return False


    def on_hover(self, event):
        if event.inaxes:
            self.last_x, self.last_y = event.xdata, event.ydata
            self.label_xy.setText('(x, y) = {0:.4f}, {1:.4f}'.format(self.last_x, self.last_y))
        else:
            self.last_x, self.last_y = np.nan, np.nan # Reset if not hovering over plot

    def keyPressEvent(self, event):
        # all key press events

        if not self.input_mode:

            if event.key == 'a' and np.isfinite(self.last_x) and np.isfinite(self.last_y) and \
                self.checkblocking('a'):
                # zooming box

                if self.plotting['box'][3] is not None:
                    self.plotting['box'][0] = self.last_x
                    self.plotting['box'][1] = self.last_y
                    self.plotting['box'][2] = None
                    self.plotting['box'][3] = None

                    self.logger.info("'a': mark the other corner of the zoom box")
                    self.plotting['blocking'] = 'a'

                elif self.plotting['box'][2] is None:
                    self.plotting['box'][2] = self.last_x
                    self.plotting['box'][3] = self.last_y

                    # rearrange
                    if self.plotting['box'][0] > self.plotting['box'][2]:
                        self.plotting['box'][0], self.plotting['box'][2] = self.plotting['box'][2], self.plotting['box'][0]
                    if self.plotting['box'][1] > self.plotting['box'][3]:
                        self.plotting['box'][1], self.plotting['box'][3] = self.plotting['box'][3], self.plotting['box'][1]
                    
                    # set plot lim
                    self.plotspec()
                    self.canvas.draw()

                    self.logger.info("'a': zoom box marked as (x0, y0, x1, y1) = {0:.2f}, {1:.2f}, {2:.2f}, {3:.2f}".format(*self.plotting['box']))
                    self.plotting['blocking'] = None

            elif event.key == 'b' and self.checkblocking('b'):
                # set y=0 baseline
                if self.plotting['box'][3] > 0:
                    self.plotting['box'][1] = 0
                else:
                    self.plotting['box'][3] = 0
                
                self.ax.set_ylim(self.plotting['box'][1], self.plotting['box'][3])
                self.canvas.draw()

                self.logger.info("'b': set (y0, y1) = {1:.2f}, {3:.2f}".format(*self.plotting['box']))
                self.plotting['blocking'] = None
            
            elif event.key == 'c':

                # clear unfinished process
                if self.plotting['ew_cont'][2] is None:
                    self.plotting['ew_cont'] = [None, None, None, None]
                if self.plotting['gauss_lim'][1] is None:
                    self.plotting['gauss_lim'] = [None, None]

                # reset plotting range
                self.plotspec(reset_lim=True)

                self.logger.info("'c': reset (x0, y0, x1, y1) to {0:.2f}, {1:.2f}, {2:.2f}, {3:.2f}".format(*self.plotting['box']))
                self.plotting['blocking'] = None

            elif event.key == 'e' and np.isfinite(self.last_x) and np.isfinite(self.last_y) and \
                self.checkblocking('e'):
                # quick EW

                if self.plotting['ew_cont'][3] is not None or self.plotting['ew_cont'][0] is None:
                    self.plotting['ew_cont'][0] = self.last_x
                    self.plotting['ew_cont'][1] = self.last_y
                    self.plotting['ew_cont'][2] = None
                    self.plotting['ew_cont'][3] = None

                    self.logger.info("'e': mark the other point for continuum level")
                    self.plotting['blocking'] = 'e'
                elif self.plotting['ew_cont'][2] is None:
                    self.plotting['ew_cont'][2] = self.last_x
                    self.plotting['ew_cont'][3] = self.last_y

                    # rearrange
                    if self.plotting['ew_cont'][2] < self.plotting['ew_cont'][0]:
                        self.plotting['ew_cont'][0], self.plotting['ew_cont'][2] = \
                            self.plotting['ew_cont'][2], self.plotting['ew_cont'][0]
                        self.plotting['ew_cont'][1], self.plotting['ew_cont'][3] = \
                            self.plotting['ew_cont'][3], self.plotting['ew_cont'][1]

                    # calculate EW
                    ew, flux = calc_ew(self.specs[0], self.plotting['ew_cont'])
                    self.plotting['ew'] = ew
                    self.plotting['flux'] = flux

                    # display
                    self.plotspec()
                    self.refresh_value_table()

                    # 
                    self.logger.info("'e': EW = {0:.6f} +- {1:.6f}; Flux = {2:.6f} +- {3:.6f}".format(*ew, *flux))
                    self.plotting['blocking'] = None
                
            elif event.key == 'k' and np.isfinite(self.last_x) and np.isfinite(self.last_y) and \
                self.checkblocking('k'):
                # quick Gaussian fitting

                if self.plotting['gauss_lim'][1] is not None or self.plotting['gauss_lim'][0] is None:
                    self.plotting['gauss_lim'][0] = self.last_x
                    self.plotting['gauss_lim'][1] = None

                    self.logger.info("'k': mark the other limit for Gaussian fitting")
                    self.plotting['blocking'] = 'k'

                elif self.plotting['gauss_lim'][1] is None:
                    self.plotting['gauss_lim'][1] = self.last_x
                    
                    # rearrange
                    if self.plotting['gauss_lim'][1] < self.plotting['gauss_lim'][0]:
                        self.plotting['gauss_lim'][0], self.plotting['gauss_lim'][1] = \
                            self.plotting['gauss_lim'][1], self.plotting['gauss_lim'][0]
                        
                    # fit gauss
                    try:
                        ew, flux, gauss_center, wmodel, smodel = fit_gauss(self.specs[0], self.plotting['gauss_lim'])
                    except:
                        ew = [np.nan, np.nan]
                        flux = [np.nan, np.nan]
                        gauss_center = [np.nan, np.nan]
                        wmodel = None
                        smodel = None

                    self.plotting['ew'] = ew
                    self.plotting['flux'] = flux
                    self.plotting['gauss_center'] = gauss_center
                    self.gauss_wave = wmodel
                    self.gauss_model = smodel

                    # display
                    self.plotspec()
                    self.refresh_value_table()

                    # 
                    self.logger.info("'k': EW = {0:.6f} +- {1:.6f}; Flux = {2:.6f} +- {3:.6f}; w0 = {4:.6f} +- {5:.6f}".format(*ew, *flux, *gauss_center))
                    self.plotting['blocking'] = None

            elif event.key == 'o':
                # zoom out wavelength

                xwidth = self.plotting['box'][2] - self.plotting['box'][0]
                self.plotting['box'][0] -= 0.1 * xwidth
                self.plotting['box'][2] += 0.1 * xwidth
                
                self.logger.info("'o': zoom out (x0, x1) to ({0:.2f}, {2:.2f})".format(*self.plotting['box']))
                self.plotspec()

            elif event.key == 'i':
                # zoom in wavelength

                xwidth = self.plotting['box'][2] - self.plotting['box'][0]
                self.plotting['box'][0] += xwidth / 12
                self.plotting['box'][2] -= xwidth / 12
                
                self.logger.info("'i': zoom in (x0, x1) to ({0:.2f}, {2:.2f})".format(*self.plotting['box']))
                self.plotspec()

            elif event.key == '+' or event.key == '=':
                # move right
                xwidth = self.plotting['box'][2] - self.plotting['box'][0]
                self.plotting['box'][0] += xwidth / 10
                self.plotting['box'][2] += xwidth / 10
                self.logger.info("'+': moving right (x0, x1) to ({0:.2f}, {2:.2f})".format(*self.plotting['box']))
                self.plotspec()

            elif event.key == '-':
                # move left
                xwidth = self.plotting['box'][2] - self.plotting['box'][0]
                self.plotting['box'][0] -= xwidth / 10
                self.plotting['box'][2] -= xwidth / 10
                self.logger.info("'-': moving left (x0, x1) to ({0:.2f}, {2:.2f})".format(*self.plotting['box']))
                self.plotspec()

            elif event.key == 'O':
                # zoom out flux

                ywidth = self.plotting['box'][3] - self.plotting['box'][1]
                self.plotting['box'][1] -= 0.1 * ywidth
                self.plotting['box'][3] += 0.1 * ywidth
                
                self.logger.info("'O': zoom out (y0, y1) to ({1:.2f}, {3:.2f})".format(*self.plotting['box']))
                self.plotspec()

            elif event.key == 'I':
                # zoom in flux

                ywidth = self.plotting['box'][3] - self.plotting['box'][1]
                self.plotting['box'][1] += ywidth / 12
                self.plotting['box'][3] -= ywidth / 12
                
                self.logger.info("'I': zoom in (y0, y1) to ({1:.2f}, {3:.2f})".format(*self.plotting['box']))
                self.plotspec()

            elif event.key == "'":
                # move up
                ywidth = self.plotting['box'][3] - self.plotting['box'][1]
                self.plotting['box'][1] += ywidth / 10
                self.plotting['box'][3] += ywidth / 10
                self.logger.info("''': moving up (y0, y1) to ({1:.2f}, {3:.2f})".format(*self.plotting['box']))
                self.plotspec()

            elif event.key == '/':
                # move down
                ywidth = self.plotting['box'][3] - self.plotting['box'][1]
                self.plotting['box'][1] -= ywidth / 10
                self.plotting['box'][3] -= ywidth / 10
                self.logger.info("'/': moving down (y0, y1) to ({1:.2f}, {3:.2f})".format(*self.plotting['box']))
                self.plotspec()

            elif event.key == 'm' and np.isfinite(self.last_x) and np.isfinite(self.last_y):
                # mark line position to set redshift

                self.input_mode = True

                self.plotting['redshift_line'] = self.last_x
                self.statusBar.showMessage("'m': input rest wavelength:")
                self.plotspec()
                self.plotting['blocking'] = 'm'
            
            elif event.key == 't' and np.isfinite(self.last_x) and np.isfinite(self.last_y):
                # mark a "trim" line
                self.plotting['trim_lines'].append(self.last_x)
                self.logger.info("'t': adding trim line at {0:.4f}".format(self.plotting['trim_lines'][-1]))
                self.plotspec()
                self.refresh_value_table()

            elif event.key == 'd' and np.isfinite(self.last_x) and np.isfinite(self.last_y):
                # remove a "trim" line
                if len(self.plotting['trim_lines']) > 0:
                    index = np.argsort(np.abs(self.plotting['trim_lines'] - self.last_x))[0]
                    tl_removed = self.plotting['trim_lines'].pop(index)

                    self.logger.info("'d': removing trim line at {0:.4f}".format(tl_removed))
                    self.plotspec()
                    self.refresh_value_table()

            elif event.key == 'r' and np.isfinite(self.last_x) and np.isfinite(self.last_y):
                # reposition a "trim" line
                if len(self.plotting['trim_lines']) > 0:
                    index = np.argsort(np.abs(self.plotting['trim_lines'] - self.last_x))[0]
                    tl_old = self.plotting['trim_lines'][index]
                    self.plotting['trim_lines'][index] = self.last_x

                    self.logger.info("'r': repositioning trim line from {0:.4f} to {1:.4f}".format(tl_old, self.plotting['trim_lines'][index]))
                    self.plotspec()
                    self.refresh_value_table()
            
            elif event.key == 's':
                # smoothing
                self.input_mode = True
                self.statusBar.showMessage("'s': input smoothing width:")
                self.plotting['blocking'] = 's'

        else:
            # input mode
            if event.key == 'escape':
                self.input_mode = False
                self.logger.info('Escaped')
                self.plotting['blocking'] = None
            elif event.key == 'backspace':
                if len(self.input_buffer) > 0:
                    del self.input_buffer[-1]
                    self.statusBar.showMessage(self.statusBar.currentMessage()[:-1])

            else:
                if self.plotting['blocking'] == 'm':
                    # in redshift marking mode
                    if event.key == 'enter':
                        # finishing input
                        final_input = ''.join(self.input_buffer)

                        try:
                            wave0 = float(final_input)
                            self.plotting['redshift'] = (self.plotting['redshift_line'] - wave0) / wave0
                            self.logger.info("'m': redshift set to {0:.6f}".format(self.plotting['redshift']))
                        except:
                            self.logger.info("'m': Input error - use non-zero numbers")
                        
                        self.input_mode = False
                        self.plotting['redshift_line'] = np.nan
                        self.plotspec()
                        self.refresh_file_table()
                        self.refresh_value_table()
                        self.input_buffer.clear()
                        self.plotting['blocking'] = None
                    else:
                        self.input_buffer.append(event.key)
                        self.statusBar.showMessage("'m': input rest wavelength: " + ''.join(self.input_buffer))

                if self.plotting['blocking'] == 's':
                    # in smoothing mode
                    if event.key == 'enter':
                        # input finished, act on spectra
                        final_input = ''.join(self.input_buffer)
                        
                        try:
                            nsmooth = int(float(final_input))
                            if len(self.specs) > 0:
                                for i, spec in enumerate(self.specs):
                                    spec.smooth(max(nsmooth, 0))
                            self.logger.info("'s': spectra smoothed with {0:d} pixels".format(nsmooth))
                        except:
                            self.logger.info("'s': input error - use integer numbers")

                        self.input_mode = False
                        self.plotspec()
                        self.refresh_file_table()
                        self.input_buffer.clear()
                        self.plotting['blocking'] = None
                    else:
                        self.input_buffer.append(event.key)
                        self.statusBar.showMessage("'s': input smoothing width: " + ''.join(self.input_buffer))
                            

    def loadspec(self, fns):

        if type(fns) == str:
            fns = [fns]
        
        if type(fns) == list:
            for i, fn in enumerate(fns):
                self.specs.append(WaveSpec.wavespec_obj(fn))

        return
    
    def loadlinelist(self, fn):
        waves, labels, kwargs = read_line_list(fn)

        self.linelist['waves'] = waves
        self.linelist['labels'] = labels
        self.linelist['kwargs'] = kwargs

        return

    def plotspec(self, reset_lim=False):

        self.ax.cla()

        for i, wavespec in enumerate(self.specs):
            self.ax.step(wavespec.wave * (wavespec.addredshift + 1), \
                         (wavespec.spec_display * wavespec.mult) + wavespec.add, \
                         where='mid', color=wavespec.color)
            if wavespec.error is not None:
                self.ax.errorbar(wavespec.wave * (wavespec.addredshift + 1), \
                             (wavespec.spec_display * wavespec.mult) + wavespec.add, \
                             yerr=wavespec.error_display * wavespec.mult, \
                             ls='none', color=wavespec.color, alpha=0.8)

        xl = self.ax.get_xlim()
        yl = self.ax.get_ylim()

        if reset_lim:
            self.plotting['box'][:] = xl[0], yl[0], xl[1], yl[1]            
        
        #if self.plotting['initial_box'][0] is None:
        #    self.plotting['initial_box'][:] = xl[0], yl[0], xl[1], yl[1]

        # reference lines
        self.ax.axhline(0, 0, 1, color='k', ls=':')

        # ew lines
        if self.plotting['ew_cont'][3] is not None:
            self.ax.plot([self.plotting['ew_cont'][0], self.plotting['ew_cont'][2]], \
                    [self.plotting['ew_cont'][1], self.plotting['ew_cont'][3]], \
                    color='red')
        # gauss
        if self.gauss_wave is not None:
            self.ax.plot(self.gauss_wave, self.gauss_model, color='red')

        # redshift line
        if np.isfinite(self.plotting['redshift_line']):
            self.ax.axvline(self.plotting['redshift_line'], 0, 1, color='red')

        # trim lines
        if len(self.plotting['trim_lines']) > 0:
            for i, tl in enumerate(self.plotting['trim_lines']):
                self.ax.axvline(tl, 0, 1, color='red')
                yw = self.plotting['box'][3] - self.plotting['box'][1]
                self.ax.text(tl, self.plotting['box'][1] + 0.0 * yw, \
                             '{0:.4f}'.format(tl), \
                             rotation=0, ha='center', va='bottom', color='red', fontsize='small')
                self.ax.text(tl / (1 + self.plotting['redshift']), self.plotting['box'][3] - 0.0 * yw, \
                             '{0:.4f}'.format(tl), \
                             rotation=0, ha='center', va='top', color='red', fontsize='small')
                
        # line list
        if len(self.linelist['waves']) > 0:
            for i, llwave in enumerate(self.linelist['waves']):
                kwargs = {**self.lldefaults, **self.linelist['kwargs'][i]}
                self.ax.axvline(llwave * (1 + self.plotting['redshift']), 0, 1, **kwargs)

                yw = self.plotting['box'][3] - self.plotting['box'][1]
                self.ax.text(llwave * (1 + self.plotting['redshift']), self.plotting['box'][1] - 0.02 * yw, \
                             self.linelist['labels'][i], \
                             rotation=-90, ha='center', va='top', color=kwargs['color'], \
                             fontsize='small')
                
        self.ax.text(0.99, 0.98, 'Redshift = {0:.6f}'.format(self.plotting['redshift']), \
                     color=self.lldefaults['color'], ha='right', va='top', transform=self.ax.transAxes)

        self.ax.set_xlim(self.plotting['box'][0], self.plotting['box'][2])
        self.ax.set_ylim(self.plotting['box'][1], self.plotting['box'][3])

        self.ax.set_xlabel('Wavelength')
        self.ax.set_ylabel('Flux')

        # secondary x
        def wave2wave0(x):
            return x / (1 + self.plotting['redshift'])
        def wave02wave(x):
            return x * (1 + self.plotting['redshift'])
        secax = self.ax.secondary_xaxis('top', functions=(wave2wave0, wave02wave))
        secax.set_xlabel('Rest Wavelength')
        
        self.canvas.draw()

        return
    
    def refresh_value_table(self):
        # refresh value table
        self.vtableWidget.blockSignals(True)

        self.vtableWidget.setRowCount(4 + len(self.plotting['trim_lines']))  # Set number of rows
        # Redshift
        item = QTableWidgetItem('Redshift')
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.vtableWidget.setItem(0, 0, item)
        item = QTableWidgetItem(str(self.plotting['redshift']))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.vtableWidget.setItem(0, 1, item)

        # Equivalent Width
        item = QTableWidgetItem('EW')
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.vtableWidget.setItem(1, 0, item)
        item = QTableWidgetItem(str(self.plotting['ew'][0]))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.vtableWidget.setItem(1, 1, item)
        item = QTableWidgetItem(str(self.plotting['ew'][1]))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.vtableWidget.setItem(1, 2, item)

        # Flux
        item = QTableWidgetItem('Flux')
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.vtableWidget.setItem(2, 0, item)
        item = QTableWidgetItem(str(self.plotting['flux'][0]))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.vtableWidget.setItem(2, 1, item)
        item = QTableWidgetItem(str(self.plotting['flux'][1]))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.vtableWidget.setItem(2, 2, item)

        # Gaussian Wave Center
        item = QTableWidgetItem('Wgauss')
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.vtableWidget.setItem(3, 0, item)
        item = QTableWidgetItem(str(self.plotting['gauss_center'][0]))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.vtableWidget.setItem(3, 1, item)
        item = QTableWidgetItem(str(self.plotting['gauss_center'][1]))
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.vtableWidget.setItem(3, 2, item)

        # Trim lines
        if len(self.plotting['trim_lines']) > 0:
            for i, tl in enumerate(self.plotting['trim_lines']):
                item = QTableWidgetItem('Trim{0:d}'.format(i))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.vtableWidget.setItem(4+i, 0, item)
                item = QTableWidgetItem(str(tl))
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.vtableWidget.setItem(4+i, 1, item)

        self.vtableWidget.blockSignals(False)
        return


    def update_color(self, cycle='default'):
        # refresh color assigments of the spectra

        if cycle=='default':
            colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

        # TODO: Add other color maps
        
        if len(self.specs) > 0:
            for i, spec in enumerate(self.specs):
                spec.color = colors[i % len(colors)]

        return
    
    def refresh_file_table(self):
        # Populate the table and set columns 1 and 2 as editable
        #self.tableWidget.setHorizontalHeaderLabels(["Filename", "Redshift", "smooth", "x", "+", "Color"])

        self.tableWidget.blockSignals(True)

        if len(self.specs) > 0:
            self.tableWidget.setRowCount(len(self.specs))  # Set number of rows

            for i, spec in enumerate(self.specs):
                items = [
                    QTableWidgetItem(os.path.basename(spec.filename)),
                    QTableWidgetItem(str(spec.addredshift)),
                    QTableWidgetItem(str(spec.smooth_width)),
                    QTableWidgetItem(str(spec.mult)),
                    QTableWidgetItem(str(spec.add)),
                    QTableWidgetItem('C{0:d}'.format(i))
                ]

                items[5].setBackground(QColor(spec.color))

                for column in range(6):
                    item = QTableWidgetItem(items[column])
                    if column in [1, 2, 3, 4]:  # Make columns 1 and 2 editable
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.tableWidget.setItem(i, column, item)

        self.tableWidget.blockSignals(False)

        return
    
    def TableItemChanged(self, item):
        # This method is called whenever an item is changed in the table
        row = item.row()
        column = item.column()
        column_name = self.tableWidget.horizontalHeaderItem(column).text()
        text = item.text()

        if column_name == '+Redshift':
            self.specs[row].addredshift = float(text)
        elif column_name == 'Smooth':
            self.specs[row].smooth(int(float(text)))
        elif column_name == 'x':
            self.specs[row].mult = float(text)
        elif column_name == '+':
            self.specs[row].add = float(text)

        self.logger.info(f"Modified table cell ({row+1}, {column_name}): {text}")
        self.plotspec()
        self.refresh_file_table()

        return

    
    def openFileNameDialog(self):

        options = QFileDialog.Options()
        # Uncomment the next line if you want a native dialog.
        #options |= QFileDialog.DontUseNativeDialog
        filenames, _ = QFileDialog.getOpenFileNames(self, "Load one or more files", "",
                                                "All Files (*);;FITS Files (*.fits *.fit *.FTS)", options=options)
        if filenames:
            self.loadspec(filenames)
            path_to_linelist = pkg_resources.resource_filename(self.package, 'lib/line_list.dat')
            self.loadlinelist(path_to_linelist)
            self.update_color()
            self.plotspec(reset_lim=True)
            self.refresh_file_table()
            self.logger.info(f"Loaded files: " + str(filenames))

    def showHelpDialog(self):
        # Create the dialog if it doesn't exist or is not visible
        if not hasattr(self, 'helpdialog') or not self.helpdialog.isVisible():
            # Dialog for displaying logs
            self.helpdialog = QDialog(self)
            self.helpdialog.setWindowTitle("Help")

            self.helpdialog.resize(600, 400)
            layout = QVBoxLayout(self.helpdialog)

            self.iconLabel = QLabel(self)
            path_to_icon = pkg_resources.resource_filename(self.package, 'lib/xtrim_icon.png')
            pixmap = QPixmap(path_to_icon)  # Replace with your icon path
            pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio)
            self.iconLabel.setPixmap(pixmap)
            self.iconLabel.setAlignment(Qt.AlignCenter)  # Center the icon

            # Add the icon label to the layout
            layout.addWidget(self.iconLabel, 1)

            # Text area for logs
            self.helptext = QTextBrowser()
            self.helptext.setReadOnly(True)
            self.helptext.setOpenExternalLinks(True)
            self.helptext.setHtml("""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; }
                        .shortcut-list { padding-left: 20px; }
                    </style>
                </head>
                <body>
                    <center><h2>XTRIM 0.1.0</h2></center>
                    <p>Designed and maintained by Yuguang Chen</p>
                    <p>For more information, visit <a href='https://github.com/yuguangchen1'>GitHub</a>.</p>

                    <h3>Shortcuts:</h3>
                    <ul class="shortcut-list">
                        <li>'a': draw a zoom box</li>
                        <li>'b': set the y-baseline at flux=0</li>
                        <li>'c': reset the plotting range</li>
                        <li>'d': delete the nearest trim line</li>
                        <li>'e': calculate an equivalent width</li>
                        <li>'i': zoom in on x-axis</li>
                        <li>Shift+'i': zoom in on y-axis</li>
                        <li>'k': fit a Gaussian function</li>
                        <li>'m': mark a rest wavelength and calculate redshift</li>
                        <li>'o': zoom out on x-axis</li>
                        <li>Shift+'o': zoom out on y-axis</li>
                        <li>'r': reposition the nearest trim line</li>
                        <li>'s': smooth all spectra</li>
                        <li>'t': add a trim line</li>
                        <li>'+': pan right</li>
                        <li>'-': pan left</li>
                        <li>'''': pan up</li>
                        <li>'/': pan down</li>
                    </ul>
                </body>
                </html>
                                  """)
            layout.addWidget(self.helptext, 10)

            self.helpdialog.setLayout(layout)
            #self.dialog.setWindowModality(Qt.WindowModal)
        
            self.helpdialog.show()  # Show the dialog

        return

def main():

    arg_parser = parser_init()
    args = arg_parser.parse_args()

    app = QApplication(sys.argv)
    ex = XtrimGUI(**vars(args))
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

