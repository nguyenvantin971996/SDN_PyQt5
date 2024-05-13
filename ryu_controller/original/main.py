import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import numpy as np
import random
import math
import json
from values import *
from makePlot import make_plot
import subprocess
import time
import requests
import statistics
import re

class Terminal(QMainWindow):

    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Terminal')
        self.setGeometry(600, 100, 600, 800)
        self.font = QFont('Arial', 15)
        self.setFont(self.font)
        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.list_paths = QPlainTextEdit(self.centralWidget)
        layout = QVBoxLayout()
        layout.addWidget(self.list_paths)
        self.centralWidget.setLayout(layout)
    
    def closeEvent(self, event):
        self.metric_show = 'bw, delay'
        self.closed.emit()
        super().closeEvent(event)

    def showEvent(self, event):
        self.metric_show = 'bw, delay'

class dynamicMetric(QMainWindow):

    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Dynamic Metric')
        self.setGeometry(1200, 100, 500, 500)
        # Create Tab Widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add tabs
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.tabs.addTab(self.tab1, "Throughput (Mbps)")
        self.tabs.addTab(self.tab2, "Latency (ms)")
        
        # Call the methods to setup each tab
        self.tab1UI()
        self.tab2UI()


        # self.tabs.currentChanged.connect(self.onTabChanged)
        
        self.metric_show = 'bw, delay'
        # self.index_tab = 0

    def tab1UI(self):
        self.layout1 = QVBoxLayout()
        self.tableWidget1 = QTableWidget()
        self.layout1.addWidget(self.tableWidget1)
        self.tab1.setLayout(self.layout1)
        self.tab1.setFont(QFont('Arial', 15))


    def tab2UI(self):       
        self.layout2 = QVBoxLayout()
        self.tableWidget2 = QTableWidget()
        self.layout2.addWidget(self.tableWidget2)
        self.tab2.setLayout(self.layout2)
        self.tab2.setFont(QFont('Arial', 15))

    def tab3UI(self):       
        self.layout3 = QVBoxLayout()
        self.tableWidget3 = QTableWidget()
        self.layout3.addWidget(self.tableWidget3)
        self.tab3.setLayout(self.layout3)
        self.tab3.setFont(QFont('Arial', 15))
    
    def closeEvent(self, event):
        self.metric_show = 'bw, delay'
        self.closed.emit()  # Emit signal when window is closed
        super().closeEvent(event)

    def showEvent(self, event):
        self.tabs.setCurrentIndex(0)
        self.metric_show = 'bw, delay'

    
    # def onTabChanged(self, index):
    #     self.index_tab = index
    #     if self.index_tab == 0:
    #         self.metric_show = 'dynamic_delay'
    #     elif self.index_tab == 1:
    #         self.metric_show = 'dynamic_bw'

class Controller(QLabel):
    def __init__(self, parent=None):
        super(Controller, self).__init__(parent)
        self.nameClass = "Controller"
        self.name = "C"
        self.id = None
        self.ip = '127.0.0.'
        self.port = 6652
        self.center = None
        self.script = None
    
    def to_dict(self):
        return {
            'nameClass': self.nameClass,
            'name': self.name,
            'id': self.id,
            'ip': self.ip,
            'port': self.port,
            'center': self.center,
            'script': self.script
        }

class Switch(QLabel):
    def __init__(self, parent=None):
        super(Switch, self).__init__(parent)
        self.nameClass = "Switch"
        self.name = "S"
        self.id = None
        self.center = None
        self.numberPorts = 0
    
    def to_dict(self):
        return {
            'nameClass': self.nameClass,
            'name': self.name,
            'id': self.id,
            'center': self.center,
            'numberPorts': self.numberPorts
        }

class Host(QLabel):
    def __init__(self, parent=None):
        super(Host, self).__init__(parent)
        self.nameClass = "Host"
        self.name = "H"
        self.id = None
        self.ip = '10.0.0.'
        self.mac = '00:00:00:00:00:'
        self.numberPorts = 0
        self.center = None
        self.server = 1
        self.command = ''
    
    def to_dict(self):
        return {
            'nameClass': self.nameClass,
            'name': self.name,
            'id': self.id,
            'ip': self.ip,
            'mac': self.mac,
            'numberPorts': self.numberPorts,
            'center': self.center,
            'server': self.server,
            'command': self.command
        }

class Link:
    def __init__(self):
        self.id = None
        self.startNode = None
        self.endNode = None
        self.port = None
        self.bw = None
        self.delay = None
        self.loss = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'startNode': self.startNode.to_dict(),
            'endNode': self.endNode.to_dict(),
            'port': self.port,
            'bw': self.bw,
            'delay': self.delay,
            'loss': self.loss
        }

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initParameters()
        

    def initUI(self):
        self.font = QFont('Arial', 15)
        self.colors = [Qt.red, Qt.green, Qt.blue, Qt.cyan, Qt.magenta]
        self.setFont(self.font)
        self.setWindowTitle("SDNLoadBalancer")
        self.setWindowIcon(QIcon("images/SDN.png"))
        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)
        # self.centralWidget.setStyleSheet('background-color: white;')
        vLayout = QVBoxLayout(self.centralWidget)
        hLayout = QHBoxLayout()
        self.nameTopo = QLabel("new.json")
        self.nameTopo.setAlignment(Qt.AlignCenter)  # Center the text horizontally
        hLayout.addStretch(1)
        hLayout.addWidget(self.nameTopo)
        hLayout.addStretch(1)
        vLayout.addLayout(hLayout)
        vLayout.addStretch(1)

        menubar = self.menuBar()
        # Create menus
        fileMenu = menubar.addMenu('File')
        componentMenu = menubar.addMenu('Component')
        editMenu = menubar.addMenu('Edit')
        actionMenu = menubar.addMenu('Action')

        fileMenu.addAction(self.addOpenAction("images/open.png", "Open"))
        fileMenu.addAction(self.addNewAction("images/new.png", "New"))
        fileMenu.addAction(self.addSaveAction("images/save.png", "Save"))
        fileMenu.addAction(self.addSaveAsAction("images/save_as.png", "Save As"))
        fileMenu.addSeparator()
        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)
        fileMenu.addAction(exitAction)

        componentMenu.addAction(self.addControllerAction("images/controller.png", "Controller"))
        componentMenu.addAction(self.addSwitchAction("images/switch.png", "Switch"))
        componentMenu.addAction(self.addHostAction("images/host.png", "Host"))
        componentMenu.addAction(self.addLinkAction("images/link.png", "Link"))

        editMenu.addAction(self.addPointerAction("images/pointer.png", "Pointer"))
        editMenu.addAction(self.addVerticalAction("images/vertical.png", "Vertical"))
        editMenu.addAction(self.addHorizontalAction("images/horizontal.png", "Horizontal"))
        editMenu.addAction(self.addTextAction("images/text.png", "Text"))

        actionMenu.addAction(self.addStartAction("images/start.png", "Start"))
        actionMenu.addAction(self.addStopAction("images/stop.png", "Stop"))
        actionMenu.addAction(self.addMonitorAction("images/table.png", "Monitoring Metrics"))
        actionMenu.addAction(self.addPlotAction("images/plot.png", "Plot Result"))
        actionMenu.addAction(self.addPathsAction("images/paths.png", "Paths"))
        actionMenu.addAction(self.addRandomAction("images/random.png", "Random"))
        actionMenu.addAction(self.addTerminalAction("images/terminal.png", "Terminal"))

        self.checkbox_bw = QAction("Show bandwidth")
        self.checkbox_delay = QAction("Show delay")
        self.checkbox_bw_delay = QAction("Show bandwidth and delay")
        self.checkbox_bw.setCheckable(True)
        self.checkbox_delay.setCheckable(True)
        self.checkbox_bw_delay.setCheckable(True)
        self.checkbox_bw_delay.setChecked(True)

        self.checkbox_bw.triggered.connect(self.handle_checkbox)
        self.checkbox_delay.triggered.connect(self.handle_checkbox)
        self.checkbox_bw_delay.triggered.connect(self.handle_checkbox)

        actionMenu.addAction(self.checkbox_bw)
        actionMenu.addAction(self.checkbox_delay)
        actionMenu.addAction(self.checkbox_bw_delay)
        

        # Left Toolbar
        self.toolbarLeft = QToolBar("Design Toolbar", self)
        self.toolbarLeft.setIconSize(QSize(60, 60))
        self.addToolBar(Qt.LeftToolBarArea, self.toolbarLeft)
        self.toolbarLeft.addAction(self.addControllerAction("images/controller.png", "Controller"))
        self.toolbarLeft.addAction(self.addSwitchAction("images/switch.png", "Switch"))
        self.toolbarLeft.addAction(self.addHostAction("images/host.png", "Host"))
        self.toolbarLeft.addAction(self.addLinkAction("images/link.png", "Link"))
        self.toolbarLeft.addAction(self.addPointerAction("images/pointer.png", "Pointer"))
        self.toolbarLeft.addAction(self.addVerticalAction("images/vertical.png", "Vertical"))
        self.toolbarLeft.addAction(self.addHorizontalAction("images/horizontal.png", "Horizontal"))
        self.toolbarLeft.addAction(self.addTextAction("images/text.png", "Text"))
        self.toolbarLeft.addAction(self.addRandomAction("images/random.png", "Random"))
        

        # Right Toolbar
        self.toolbarRight = QToolBar("File Toolbar", self)
        self.toolbarRight.setIconSize(QSize(60, 60))
        self.addToolBar(Qt.RightToolBarArea, self.toolbarRight)
        self.toolbarRight.addAction(self.addOpenAction("images/open.png", "Open"))
        self.toolbarRight.addAction(self.addNewAction("images/new.png", "New"))
        self.toolbarRight.addAction(self.addSaveAction("images/save.png", "Save"))
        self.toolbarRight.addAction(self.addSaveAsAction("images/save_as.png", "Save As"))
        self.toolbarRight.addAction(self.addStartAction("images/start.png", "Start"))
        self.toolbarRight.addAction(self.addStopAction("images/stop.png", "Stop"))
        self.toolbarRight.addAction(self.addMonitorAction("images/table.png", "Monitoring Metrics"))
        self.toolbarRight.addAction(self.addPlotAction("images/plot.png", "Plot Result"))
        self.toolbarRight.addAction(self.addPathsAction("images/paths.png", "Paths"))
        self.toolbarRight.addAction(self.addTerminalAction("images/terminal.png", "Terminal"))
        
        
        self.fileName = None

        self.imagePath = None
        self.actionText = "Pointer"
        self.pixmap = None

        self.lastMousePosition = None
        self.textToAdd = None

        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = None

        self.showMaximized()
        self.show()
    
    def initParameters(self):
        self.controllers = []
        self.switches = []
        self.hosts = []
        self.links = []
        self.n_controllers = 0
        self.n_switches = 0
        self.n_hosts = 0
        self.n_links = 0
        self.link_link = []
        self.linksToPaint = []
        self.linksPainted = []
        self.linksHost = []
        self.selectedNodes = []
        self.labels = []
        self.timer = QTimer(self)
        self.mininet_process = None
        self.ryu_process = None
        self.dynamic_metric = dynamicMetric()
        self.dynamic_metric.closed.connect(self.update)
        self.terminal = Terminal()
        self.terminal.closed.connect(self.update)
        self.checkToOpen = True
        self.n_paths = 0
        self.nodeSelected = None
        self.linkSelected = None
        self.fileNameMininet = None
        self.fileNameRyu = None
        
    
    def handle_checkbox(self, checked):
        # Get the checkbox that emitted the signal
        sender = self.sender()
        # Uncheck all other checkboxes
        for checkbox in [self.checkbox_bw, self.checkbox_delay, self.checkbox_bw_delay]:
            if checkbox != sender:
                checkbox.setChecked(False)
        if self.checkbox_bw.isChecked():
            self.dynamic_metric.metric_show = 'bw'
        elif self.checkbox_delay.isChecked():
            self.dynamic_metric.metric_show = 'delay'
        elif self.checkbox_bw_delay.isChecked():
            self.dynamic_metric.metric_show = 'bw, delay'
        else:
            self.dynamic_metric.metric_show = 'bw, delay'
        self.update()
    
    def closeEvent(self, event):
        self.dynamic_metric.close()
        self.terminal.close()

    # LEFT TOOLBAR
    def addControllerAction(self, iconPath, actionText):
        # Create an action with an icon
        action = QAction(QIcon(iconPath), actionText, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, actionText))
        return action
    
    def addSwitchAction(self, iconPath, actionText):
        # Create an action with an icon
        action = QAction(QIcon(iconPath), actionText, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, actionText))
        return action
    
    def addHostAction(self, iconPath, actionText):
        # Create an action with an icon
        action = QAction(QIcon(iconPath), actionText, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, actionText))
        return action

    def addLinkAction(self, iconPath, actionText):
        # Create an action with an icon
        action = QAction(QIcon(iconPath), actionText, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, actionText))
        return action

    def addPointerAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, actionText))
        return action
    
    def addVerticalAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(lambda: self.selectedMode(iconPath, "Pointer"))
        action.triggered.connect(self.Vertical)
        return action

    def addHorizontalAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(lambda: self.selectedMode(iconPath, "Pointer"))
        action.triggered.connect(self.Horizontal)
        return action

    def addRandomAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, actionText))
        action.triggered.connect(self.makeRandom)
        return action
    
    def addTextAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, "Text"))
        return action
    
    def getAction(self, toolbar, text):
        for action in toolbar.actions():
            if action.text() == text:
                return action
        return None
    
    def setActive(self, action):
        for act in self.toolbarLeft.actions():
            act.setChecked(False)
        action.setChecked(True)
        if action.text() != "Text":
            if self.textToAdd != None:
                self.textToAdd.deleteLater()
                self.textToAdd = None
    
    def selectedMode(self, imagePath, actionText):
        # Update the label when an image is selected
        if len(self.link_link) % 2 == 1:
            self.link_link.pop()
        if actionText in ("Pointer", "Link", "Text", "Random"):
            self.imagePath = None
            self.actionText = actionText
            self.pixmap = None
        else:
            self.imagePath = imagePath
            self.actionText = actionText
            if self.imagePath:
                self.pixmap = QPixmap(self.imagePath).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                self.pixmap = None
    
    def Cancel(self):
        for label in self.selectedNodes:
            label.setStyleSheet("""
                                    QLabel {
                                        font-family: 'Arial';
                                        font-size: 15pt;
                                            }
                                    """)
        self.selectedNodes = []
    
    def Vertical(self):
        if self.textToAdd != None:
                self.textToAdd.deleteLater()
                self.textToAdd = None
        for act in self.toolbarLeft.actions():
            act.setChecked(False)
        actionPointer = self.getAction(self.toolbarLeft, "Pointer")
        actionPointer.setChecked(True)
        if len(self.selectedNodes)!= 0:
            x = 0
            for label in self.selectedNodes:
                x += label.x()
            x_tb = int(x/len(self.selectedNodes))
            for label in self.selectedNodes:
                y = label.y()
                label.move(x_tb, y)
                self.updateNodePosition(label)
            self.Cancel()
            self.update()
    
    def Horizontal(self):
        if self.textToAdd != None:
                self.textToAdd.deleteLater()
                self.textToAdd = None
        for act in self.toolbarLeft.actions():
            act.setChecked(False)
        actionPointer = self.getAction(self.toolbarLeft, "Pointer")
        actionPointer.setChecked(True)
        if len(self.selectedNodes)!= 0:
            y = 0
            for label in self.selectedNodes:
                y += label.y()
            y_tb = int(y/len(self.selectedNodes))
            for label in self.selectedNodes:
                x = label.x()
                label.move(x, y_tb)
                self.updateNodePosition(label)
            self.Cancel()
            self.update()
    
    def makeRandom(self):
        for link in self.links:
            if isinstance(link.startNode, Host) or isinstance(link.endNode, Host):
                link.delay = random.choice(valuesDelayHost)
                link.bw = random.choice(valuesBwHost)
                link.loss = random.choice(valuesLoss)
            else:
                link.delay = random.choice(valuesDelay)
                link.bw = random.choice(valuesBw)
                link.loss = random.choice(valuesLoss)
        self.update()
    
    def placeText(self):
        # Create a label at the position of the text input field with the entered text
        text = self.textToAdd.text()
        label = QLabel(text, self)
        label.adjustSize()
        label.move(self.textToAdd.pos())
        label.show()
        self.labels.append(label)
        self.textToAdd.deleteLater()
        self.textToAdd = None

    def addTextAtPosition(self, event):
        # Get the position of the mouse click and place the text input field there
        position = event.pos()
        self.textToAdd.move(position)
        self.textToAdd.show()
        self.textToAdd.setFocus()
    
    # RIGHT TOOLBAR
    def addOpenAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.openTopo)
        return action

    def addNewAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.New)
        return action
    
    def addSaveAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.Save)
        return action

    def addSaveAsAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.SaveAs)
        return action

    def addStartAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.Start)
        return action

    def addStopAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.Stop)
        return action

    def addPlotAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.plotChart)
        return action

    def addMonitorAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self) 
        action.triggered.connect(self.monitor)
        return action

    def addPathsAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.plotPaths)
        return action

    def addTerminalAction(self, iconPath, actionText):
        action = QAction(QIcon(iconPath), actionText, self)
        action.triggered.connect(self.show_terminal)
        return action

    def plotPaths(self):
        if self.n_paths < (len(self.linksToPaint)-1):
            self.n_paths += 1
        else:
            self.n_paths = -1
        self.update()

    def show_terminal(self):
        self.terminal.show()
        self.update()

    def monitor(self):
        self.dynamic_metric.show()
        self.update()
    
    def openTopo(self):
        options = QFileDialog.Options()
        self.fileName, _ = QFileDialog.getOpenFileName(self, "Open File", "topo_mininet/", "JSON Files (*.json);;All Files (*)", options=options)
        if self.fileName:
            self.refreshSpace()
            self.initParameters()
            self.loadTopo(self.fileName)
            self.nameTopo.setText(os.path.basename(self.fileName))
            base_name = os.path.splitext(self.fileName)[0]
            self.fileNameMininet = f'{base_name}.py'
            self.makeTraffic()
        self.selectedMode("images/pointer.png", "Pointer")
        for act in self.toolbarLeft.actions():
            act.setChecked(False)
        actionPointer = self.getAction(self.toolbarLeft, "Pointer")
        actionPointer.setChecked(True)
        self.n_controllers += len(self.controllers)
        self.n_switches += len(self.switches)
        self.n_hosts += len(self.hosts)
        self.n_links += len(self.links)

    def refreshSpace(self):
        for item in self.controllers+self.hosts+self.switches+self.labels:
            item.deleteLater()
            item = None
        self.update()
    
    def loadTopo(self, fileName):
        try:
            with open(fileName, 'r') as file:
                # Assuming you are loading JSON data for the topology
                topoData = json.load(file)
                self.getInfo(topoData)
                self.update()
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Failed to open the topology: {e}")
    
    def getInfo(self, topoData):
        for item in topoData['controllers']:
            newNode = self.loadNode("Controller", item)
            self.nodeDraw(newNode)
            self.controllers.append(newNode)

        for item in topoData['hosts']:
            newNode = self.loadNode("Host", item)
            self.nodeDraw(newNode)
            self.hosts.append(newNode)

        for item in topoData['switches']:
            newNode = self.loadNode("Switch", item)
            self.nodeDraw(newNode)
            self.switches.append(newNode)
        
        for item in topoData['labels']:
            text = item['text']
            label = QLabel(text, self)
            label.adjustSize()
            label.move(item['pos'][0], item['pos'][1])
            label.show()
            self.labels.append(label)

        for item in topoData['links']:
            link = Link()
            link.id = item['id']
            name_class_start = item['startNode']['nameClass']
            startNode = self.loadNode(name_class_start, item['startNode'])
            link.startNode = self.getNode(startNode)
            name_class_end = item['endNode']['nameClass']
            endNode = self.loadNode(name_class_end, item['endNode'])
            link.endNode = self.getNode(endNode)
            link.delay = item['delay']
            link.bw = item['bw']
            link.loss = item['loss']
            link.port = item['port']
            self.links.append(link)

    def nodeDraw(self, newNode):
        newNode.setPixmap(self.pixmap)
        newNode.setFixedSize(self.pixmap.size())
        x = newNode.center[0] - self.pixmap.width()//2
        y = newNode.center[1] - self.pixmap.height()//2
        newNode.move(x, y)
        newNode.show()

    def getNode(self, startNode):
        if startNode.nameClass == "Controller":
            for ctr in self.controllers:
                if ctr.id == startNode.id:
                    return ctr
        elif startNode.nameClass == "Switch":
            for ctr in self.switches:
                if ctr.id == startNode.id:
                    return ctr
        else:
            for ctr in self.hosts:
                if ctr.id == startNode.id:
                    return ctr

    def loadNode(self, nameClass, item):
        if nameClass == "Controller":
            self.selectedMode("images/controller.png", "Controller")
            newNode = Controller(self)
            newNode.id = item['id']
            newNode.center = item['center']
            newNode.name = item['name']
            newNode.ip = item['ip']
            newNode.port = item['port']
            newNode.script = item['script']
            self.fileNameRyu = newNode.script
            return newNode
        elif nameClass == "Switch":
            self.selectedMode("images/switch.png", "Switch")
            newNode = Switch(self)
            newNode.id = item['id']
            newNode.center = item['center']
            newNode.name = item['name']
            newNode.numberPorts = item['numberPorts']
            return newNode
        else:
            self.selectedMode("images/host.png", "Host")
            newNode = Host(self)
            newNode.id = item['id']
            newNode.center = item['center']
            newNode.name = item['name']
            newNode.ip = item['ip']
            newNode.mac = item['mac']
            newNode.numberPorts = item['numberPorts']
            newNode.server = item['server']
            newNode.command = item['command']
            return newNode
    
    def New(self):
        self.nameTopo.setText("new.json")
        self.fileName = None
        self.refreshSpace()
        self.initParameters()

    def Save(self):
        if self.fileName:
            with open(self.fileName, 'w') as f:
                topo_json = self.makeTopoJson()
                f.write(topo_json)
            f.close()
            base_name = os.path.splitext(self.fileName)[0]
            self.fileNameMininet = f'{base_name}.py'
            self.makeScript(self.fileNameMininet)
            self.makeTraffic()
        else:
            self.SaveAs()
    
    def makeTopoJson(self):
        topoData = {}
        
        topoData['controllers'] = []
        for ctr in self.controllers:
            topoData['controllers'].append(ctr.to_dict())
        
        topoData['switches'] = []
        for sw in self.switches:
            topoData['switches'].append(sw.to_dict())
        
        topoData['hosts'] = []
        for hst in self.hosts:
            topoData['hosts'].append(hst.to_dict())

        topoData['links'] = []
        for lk in self.links:
            topoData['links'].append(lk.to_dict())

        topoData['labels'] = []
        for lb in self.labels:
            lb_dict = {}
            lb_dict['text'] = lb.text()
            lb_dict['pos'] = (lb.x(), lb.y())
            topoData['labels'].append(lb_dict)
        
        topo_json = json.dumps(topoData, indent=4)
        return topo_json

    def SaveAs(self):
        options = QFileDialog.Options()
        defaultFileName = "topo_mininet/topology.json"  # Set a default file name
        fileName, _ = QFileDialog.getSaveFileName(self, "Save As Topology", defaultFileName, "JSON Files (*.json);;All Files (*)", options=options)

        if fileName:
            if not fileName.endswith('.json'):
                fileName += '.json'  # Ensure the file has a .json extension

            with open(fileName, 'w') as f:
                topo_json = self.makeTopoJson()
                f.write(topo_json)
            f.close()

            self.nameTopo.setText(os.path.basename(fileName))
            self.fileName = fileName
            base_name = os.path.splitext(self.fileName)[0]
            self.fileNameMininet = f'{base_name}.py'
            self.makeScript(self.fileNameMininet)
            self.makeTraffic()
            
    
    def makeTraffic(self):
        for host in self.hosts:
            with open("traffic/{}.sh".format(host.name), 'w') as f:
                f.write(host.command)
            f.close()


    def makeScript(self, fileName):
        try:
            with open(fileName, 'w') as f:
                lib = self.makeString()
                f.write(lib)
            f.close()
            QMessageBox.information(self, "Save", "Save topology and mininet script successfully!")
        except ValueError:
            QMessageBox.warning(self, "Error", "Can not save topology and mininet script. Check network!")
    
    def makeString(self):
        body = s1

        host_str = ""
        for host in self.hosts:
            h = "\t\t{} = self.addHost('{}', mac='{}', ip='{}')\n".format(host.name, host.name, host.mac, host.ip)
            host_str = host_str + h
        
        sw_str = ""
        for swt in self.switches:
            sw = "\t\t{} = self.addSwitch('{}')\n".format(swt.name, swt.name)
            sw_str = sw_str + sw
        
        link_str = ""
        for lk in self.links:
            l = "\t\tself.addLink({}, {}, {}, {}, bw={}, delay='{}ms', loss={})\n".format(lk.startNode.name, lk.endNode.name, lk.port[0], lk.port[1], lk.bw, lk.delay, lk.loss)
            link_str = link_str + l

        ctr_str = ""
        for ctr in self.controllers:
            ctr_ = "\tnet = Mininet(topo=topo, controller=RemoteController(name='{}', ip='{}', port={}), link=link)\n".format(ctr.name, ctr.ip, ctr.port)
            ctr_str = ctr_str + ctr_
        ctr_str += "\tnet.start()\n\tsleep(5)\n"

        hs = ""
        for host in self.hosts:
            if host.server == 1:
                hs += "\tmakeTerm(net['{}'],cmd='bash traffic/{}.sh')\n".format(host.name, host.name)
        hs += "\tsleep(2)\n"
        for host in self.hosts:
            if host.server == 0:
                hs += "\tmakeTerm(net['{}'],cmd='bash traffic/{}.sh')\n".format(host.name, host.name)

        body = body + host_str + sw_str + link_str + s2 + ctr_str + hs + s3
        return body
        
    
    def Start(self):
        if self.ryu_process and self.ryu_process.poll() is None:
            QMessageBox.warning(self, "Ryu controller", "Ryu controller is already running!")
            return
        if self.mininet_process and self.mininet_process.poll() is None:
            QMessageBox.warning(self, "Mininet", "Mininet is already running!")
            return
        try:
            # Start the Ryu controller
            self.ryu_process = subprocess.Popen(['xterm', '-e', "ryu-manager", "--observe-links", self.fileNameRyu], stdout=subprocess.PIPE)
        except ValueError:
            QMessageBox.warning(self, "Ryu controller", "Can not start Ryu controller!")
        
        time.sleep(2)

        try:
        # Start Mininet with the custom topology
            self.mininet_process = subprocess.Popen(['xterm', '-e', "sudo", "python3", self.fileNameMininet], stdout=subprocess.PIPE)
        except ValueError:
            QMessageBox.warning(self, "Mininet", "Can not start Mininet!")

        # Note: You could also start Mininet with its Python API inside a thread if you want to interact with it programmatically.
        self.timer.timeout.connect(lambda: self.display_metrics(self.dynamic_metric.tableWidget1, 'throughput'))
        self.timer.timeout.connect(lambda: self.display_metrics(self.dynamic_metric.tableWidget2, 'latency'))
        
        self.timer.timeout.connect(self.get_paths)
        update_interval = 2000
        self.timer.start(update_interval)
    
    def get_paths(self):
        try:
            response = requests.get("http://localhost:8080/paths")
            if response.status_code == 200:
                paths_dict = response.json()
                if paths_dict != None:
                    if len(paths_dict) != 0:
                        self.linksToPaint = []
                        self.linksHost = []
                        terminal_string = ''
                        for key_0, pths in paths_dict.items():
                            terminal_string += pths[-1] + '\n'
                            paths = []
                            lksHost = []
                            c = True
                            for path in pths[1]:
                                
                                pth = []
                                for link in path:
                                    for lk in self.links:
                                        if lk.startNode.id in link and lk.endNode.id in link and lk not in pth and lk.startNode.nameClass == "Switch" and lk.endNode.nameClass == "Switch":
                                            pth.append(lk)
                                            break

                                paths.append(pth)

                                if c:
                                    for lk in self.links:
                                        if (lk.startNode.nameClass == "Host" and lk.startNode.ip == pths[3] or lk.endNode.nameClass == "Host" and lk.endNode.ip == pths[3]) and lk not in lksHost:
                                            lksHost.append(lk)
                                            continue
                                        if (lk.startNode.nameClass == "Host" and lk.startNode.ip == pths[4] or lk.endNode.nameClass == "Host" and lk.endNode.ip == pths[4]) and lk not in lksHost:
                                            lksHost.append(lk)
                                            continue
                                c = False

                            for key in range(len(pths[0])):
                                int_string = 'Path ' + str(key+1) + ': [' + ', '.join(map(str, pths[0][key])) + '], length = ' + str(pths[2][key]) + '\n'
                                terminal_string += int_string
                            if len(paths_dict) > 1:
                                side = '\n'
                                terminal_string += side

                            self.linksToPaint.append(paths)
                            self.linksHost.append(lksHost)
                        
                        self.terminal.list_paths.setPlainText(terminal_string)
                        self.terminal.show()
                        self.update()
            else:
                print(f"Error: Received status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
    
    def display_metrics(self, tableWidget, metric):
        try:
            link_api = "http://localhost:8080/" + metric
            response = requests.get(link_api)
            if response.status_code == 200:
                metrics = response.json()
                if metrics != None:
                    if len(metrics) != 0:
                        tableWidget.clearContents()
                        tableWidget.setRowCount(len(metrics))
                        tableWidget.setColumnCount(len(metrics))
                        c = 0
                        for i in range(len(metrics)):
                            d = True
                            while d:
                                for key, nested in metrics.items():
                                    if int(key) == (i+1+c):
                                        header_item = QTableWidgetItem("S" + key)
                                        tableWidget.setHorizontalHeaderItem(i, header_item)
                                        d = False
                                        break
                                if d:
                                    c+=1
        
                        c = 0
                        for i in range(len(metrics)):
                            d = True
                            while d:
                                for key, nested in metrics.items():
                                    if int(key) == (i+1+c):
                                        header_item = QTableWidgetItem("S" + key)
                                        tableWidget.setVerticalHeaderItem(i, header_item)
                                        d = False
                                        break
                                if d:
                                    c+=1
                        
                        for key, nested in metrics.items():
                            for nested_key, nested_value in nested.items():
                                item = QTableWidgetItem(str(nested_value))
                                item.setTextAlignment(Qt.AlignCenter)

                                for i in range(tableWidget.rowCount()):
                                    dk = False
                                    for j in range(tableWidget.columnCount()):
                                        if tableWidget.verticalHeaderItem(j).text() == ("S" + nested_key) and tableWidget.horizontalHeaderItem(i).text() == ("S" + key):
                                            tableWidget.setItem(i, j, item)
                                            dk = True
                                            break
                                    if dk:
                                        break
                        
                        width = tableWidget.verticalHeader().width() + 30
                        height = tableWidget.horizontalHeader().height() + 60

                        for i in range(tableWidget.columnCount()):
                            tableWidget.setColumnWidth(i, 60)
                            width += tableWidget.columnWidth(i)
                        
                        for i in range(tableWidget.rowCount()):
                            height += tableWidget.rowHeight(i)
                        self.dynamic_metric.resize(width, height)
                        if self.checkToOpen:
                            self.dynamic_metric.show()
                            self.checkToOpen = False

                        self.update()

            else:
                print(f"Error: Received status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")

    def Stop(self):
        try:
            if self.ryu_process:
                self.ryu_process.terminate()
                time.sleep(2)  # Wait for graceful termination
                if self.ryu_process.poll() is None:  # Still running
                    self.ryu_process.kill()  # Force termination
                self.ryu_process = None

            if self.mininet_process:
                self.mininet_process.terminate()
                time.sleep(2)
                if self.mininet_process.poll() is None:
                    self.mininet_process.kill()
                self.mininet_process = None
            self.cleanup_network()
            self.dynamic_metric.close()
            self.terminal.close()
            self.checkToOpen = True
            # self.dynamic_metric.metric_show = 'delay'
            # self.linksToPaint = []
            # self.linksHost = []
            # self.n_paths = 0
            self.timer.stop()
            self.update()
        except Exception as e:
            QMessageBox.warning(self, "Cleanup", f"Error stopping network: {str(e)}")
    
    def cleanup_network(self):
        try:
            cleanup_iperf = subprocess.Popen(['xterm', '-e', 'sudo', 'pkill', '-f', 'iperf3'])
            # cleanup_ditg = subprocess.Popen(['xterm', '-e', 'sudo', 'pkill', '-f', 'ITGRecv'])
            cleanup_ryu = subprocess.Popen(['xterm', '-e', 'sudo', 'pkill', 'ryu-manager'])
            cleanup_mininet = subprocess.Popen(['xterm', '-e', 'sudo', 'mn', '-c'])
            time.sleep(2)
            QMessageBox.information(self, "Cleanup", "Clean Ryu controller and Mininet successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Cleanup", f"Cleanup Exception: {str(e)}")

    def plotChart(self):
        while True:
            fileNames, _ = QFileDialog.getOpenFileNames(self, "Plot result", "result/", "JSON Files (*.json)")
            if fileNames:
                try:
                    make_plot(fileNames)
                    break
                except:
                    continue
            else:
                break

    # EVENT
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.nodeSelected = self.getNodeAtPosition(event.pos())
        self.linkSelected = self.getLinkAtPosition(event.pos())
        self.lastMousePosition = event.pos()
        
        if self.actionText == "Pointer":
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, self.origin))
            self.rubberBand.show()

        if event.button() == Qt.LeftButton:
            if self.nodeSelected == None and self.actionText == "Pointer":
                self.Cancel()
            else:
                self.placeImage(event.pos())
                if self.actionText == "Link":
                    self.prepareLine(self.nodeSelected)
        elif event.button() == Qt.RightButton and self.nodeSelected not in self.labels:
            self.checkForMetricRightClick(event.pos())
            self.openNodeDialog()
        
        if self.actionText == "Text":
            if self.textToAdd == None:
                self.textToAdd = QLineEdit(self)
                self.textToAdd.setPlaceholderText("Enter text here")
                self.addTextAtPosition(event)
                self.textToAdd.returnPressed.connect(self.placeText)
            else:
                self.addTextAtPosition(event)
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.origin is not None and self.nodeSelected == None:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
        if self.actionText == "Pointer":
            if len(self.selectedNodes)!=0:
                if self.nodeSelected in self.selectedNodes:
                    for node in self.selectedNodes:
                        # Calculate the distance moved
                        delta = event.pos() - self.lastMousePosition
                        # Move the selected label
                        new_pos = node.pos() + delta
                        node.move(new_pos)
                        # Update the position in the dictionary
                        self.updateNodePosition(node)
            elif self.nodeSelected != None:
                # Calculate the distance moved
                delta = event.pos() - self.lastMousePosition
                # Move the selected label
                new_pos = self.nodeSelected.pos() + delta
                self.nodeSelected.move(new_pos)
                # Update the position in the dictionary
                self.updateNodePosition(self.nodeSelected)
            self.lastMousePosition = event.pos()
        # Redraw lines
        self.update()
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.origin is not None:
            self.rubberBand.hide()
            rect = self.rubberBand.geometry()
            self.selectLabels(rect)
            self.origin = None
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            if self.linkSelected:
                self.deleteSelectedLink(self.linkSelected)
            if len(self.selectedNodes) != 0:
                self.deleteNodes()
    
    def placeImage(self, position):
        if self.pixmap and not self.pixmap.isNull():
            self.addNode(position)
    
    def addNode(self, position):
        if self.actionText == "Controller":
            newNode = Controller(self)
            self.n_controllers += 1
            list_id_ctr = [item.id for item in self.controllers]
            for i in range(1, self.n_controllers+1):
                if i not in list_id_ctr:
                    newNode.id = i
                    break
            newNode.setPixmap(self.pixmap)
            newNode.setFixedSize(self.pixmap.size())
            x = position.x() - self.pixmap.width()//2
            y = position.y() - self.pixmap.height()//2
            newNode.move(x, y)
            newNode.show()
            newNode.center = (position.x(), position.y())
            newNode.name = newNode.name + str(newNode.id)
            newNode.ip = newNode.ip + str(newNode.id)
            newNode.port = newNode.port + newNode.id
            self.controllers.append(newNode)
        
        elif self.actionText == "Switch":
            newNode = Switch(self)
            self.n_switches += 1
            list_id_sw = [item.id for item in self.switches]
            for i in range(1, self.n_switches+1):
                if i not in list_id_sw:
                    newNode.id = i
                    break
            newNode.setPixmap(self.pixmap)
            newNode.setFixedSize(self.pixmap.size())
            x = position.x() - self.pixmap.width()//2
            y = position.y() - self.pixmap.height()//2
            newNode.move(x, y)
            newNode.show()
            newNode.center = (position.x(), position.y())
            newNode.name = newNode.name + str(newNode.id)
            self.switches.append(newNode)

        elif self.actionText == "Host":
            newNode = Host(self)
            self.n_hosts += 1
            list_id_h = [item.id for item in self.hosts]
            for i in range(1, self.n_hosts+1):
                if i not in list_id_h:
                    newNode.id = i
                    break
            newNode.setPixmap(self.pixmap)
            newNode.setFixedSize(self.pixmap.size())
            x = position.x() - self.pixmap.width()//2
            y = position.y() - self.pixmap.height()//2
            newNode.move(x, y)
            newNode.show()
            newNode.center = (position.x(), position.y())
            newNode.name = newNode.name + str(newNode.id)
            if newNode.id < 10:
                newNode.mac = newNode.mac + '0' + str(newNode.id)
            elif 10 <= newNode.id < 100:
                newNode.mac = newNode.mac + str(newNode.id)
            else:
                QMessageBox.warning(self, "Invalid Input", "Number of hosts is only lower than 100.")
            newNode.ip = newNode.ip + str(newNode.id)
            self.hosts.append(newNode)
        self.update()

    def getNodeAtPosition(self, position):
        # Find the label at the given position
        for label in self.findChildren(QLabel):
            if label.geometry().contains(position):
                return label
        return None
    
    def getLinkAtPosition(self, position):
        # This method should return the link if a delay label is clicked
        for link in self.links:
            startNode = link.startNode
            endNode = link.endNode
            start_pos = startNode.center
            end_pos = endNode.center
            mid_point = QPoint(int((start_pos[0] + end_pos[0]) / 2), int((start_pos[1] + end_pos[1]) / 2))

            # Calculate the bounding box for the delay text
            metric_text = str(link.delay)
            text_width = self.fontMetrics().width(metric_text)
            text_height = self.fontMetrics().height()
            text_rect = QRect(int(mid_point.x() - text_width / 2), int(mid_point.y() - text_height / 2),
                            text_width, text_height)

            # Check if the click is within the bounding box of the delay text
            if text_rect.contains(position):
                return link
        return None
    
    def prepareLine(self, closestNode):
        if closestNode and not(isinstance(closestNode, Controller)) and closestNode not in self.labels:
            if len(self.link_link) % 2 == 1:
                if not(self.link_link[-1] is closestNode):
                    self.link_link.append(closestNode)
                    self.update()  # Trigger a repaint to draw the new line
                    
                    link = Link()
                    self.n_links += 1
                    id = self.n_links
                    link.id = id
                    link.startNode = self.link_link[-2]
                    link.endNode = self.link_link[-1]
                    link.startNode.numberPorts += 1
                    link.endNode.numberPorts += 1
                    link.port = [link.startNode.numberPorts, link.endNode.numberPorts]
                    if isinstance(link.startNode, Host) or isinstance(link.endNode, Host):
                        link.delay = random.choice(valuesDelayHost)
                        link.bw = random.choice(valuesBwHost)
                        link.loss = random.choice(valuesLoss)
                    else:
                        link.delay = random.choice(valuesDelay)
                        link.bw = random.choice(valuesBw)
                        link.loss = random.choice(valuesLoss)
                    cond = True
                    for lk in self.links:
                        if set((link.startNode, link.endNode)) == set((lk.startNode, lk.endNode)):
                            cond = False
                    if cond:
                        self.links.append(link)
            else:
                self.link_link.append(closestNode)
    
    def updateNodePosition(self, label):
        # Call this method whenever you move the label around
        x, y = label.x(), label.y()
        center_pos = (x + label.width()//2, y + label.height()//2)
        label.center = center_pos

    def selectLabels(self, rect):
        for label in self.controllers+self.hosts+self.switches+self.labels:
            # Check if the QLabel geometry intersects with the selection rectangle
            if rect.intersects(label.geometry()) and label not in self.selectedNodes:
                self.selectedNodes.append(label)
        if len(self.selectedNodes)>0:
            for label in self.selectedNodes:
                label.setStyleSheet("""
                                    QLabel {
                                        border: 2px solid blue;
                                        font-family: 'Arial';
                                        font-size: 15pt;
                                            }
                                    """)

    def checkForMetricRightClick(self, position):
        for link in self.links:
            startNode = link.startNode
            endNode = link.endNode
            start_pos = startNode.center
            end_pos = endNode.center
            mid_point = QPoint(int((start_pos[0] + end_pos[0]) / 2), int((start_pos[1] + end_pos[1]) / 2))

            # Calculate the bounding box for the delay text
            cur_delay = str(link.delay)
            cur_bw = str(link.bw)
            cur_loss = str(link.loss)
            text_width = self.fontMetrics().width(cur_delay + " ms")
            text_height = self.fontMetrics().height()
            text_rect = QRect(int(mid_point.x() - text_width / 2), int(mid_point.y() - text_height / 2),
                            text_width, text_height)

            # Check if the click is within the bounding box of the delay text
            if text_rect.contains(position):
                self.openMetricDialog(link, cur_delay, cur_bw, cur_loss)
                break

    def openMetricDialog(self, link, cur_delay, cur_bw, cur_loss):
        dialog = QDialog()
        dialog.setMinimumSize((QSize(400, 250)))
        dialog.setFont(self.font)
        title = "Metric of link {}-{}".format(link.startNode.name, link.endNode.name)
        dialog.setWindowTitle(title)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        bw_label = QLabel("Set bandwidth (Mbps):", dialog)
        layout.addWidget(bw_label)
        bw = QLineEdit(dialog)
        bw.setText(cur_bw)
        layout.addWidget(bw)

        delay_label = QLabel("Set delay (ms):", dialog)
        layout.addWidget(delay_label)
        delay = QLineEdit(dialog)
        delay.setText(cur_delay)
        layout.addWidget(delay)

        loss_label = QLabel("Set loss (%):", dialog)
        layout.addWidget(loss_label)
        loss = QLineEdit(dialog)
        loss.setText(cur_loss)
        layout.addWidget(loss)

        h_layout = QHBoxLayout()
        button_change = QPushButton('Apply')
        button_change.clicked.connect(lambda: self.changeLinkMetric(dialog, link, delay.text(), bw.text(), loss.text()))
        button_close = QPushButton('Close')
        button_close.clicked.connect(dialog.reject)
        h_layout.addStretch(1)
        h_layout.addWidget(button_close)
        h_layout.addWidget(button_change)
        layout.addLayout(h_layout)

        # Execute the dialog and wait for the user to close it
        result = dialog.exec()

    def changeLinkMetric(self, dialog, link, delay, bw, loss):
        # Here you would validate and then update the delay for the link
        try:
            link.delay = int(delay)
            link.bw = int(bw)
            link.loss = int(loss)
            self.update()
            dialog.reject()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Check type of input.")

    def openNodeDialog(self):
        if self.nodeSelected:
            dialog = QDialog()
            dialog.setFont(self.font)
            title = "Parameters of " + self.nodeSelected.name
            dialog.setWindowTitle(title)

            layout = QVBoxLayout()
            dialog.setLayout(layout)

            if self.nodeSelected.nameClass == "Controller":
                dialog.setMinimumSize((QSize(600, 300)))
                id_label = QLabel("ID: "+str(self.nodeSelected.id), dialog)
                layout.addWidget(id_label)

                ip_label = QLabel("Set IP:", dialog)
                layout.addWidget(ip_label)
                ip = QLineEdit(dialog)
                ip.setText(self.nodeSelected.ip)
                layout.addWidget(ip)

                port_label = QLabel("Set port:", dialog)
                layout.addWidget(port_label)
                port = QLineEdit(dialog)
                port.setText(str(self.nodeSelected.port))
                layout.addWidget(port)

                sr_label = QLabel("Choose script:", dialog)
                layout.addWidget(sr_label)
                h_layout = QHBoxLayout()
                sr = QLineEdit(dialog)
                sr.setText(str(self.nodeSelected.script))
                h_layout.addWidget(sr)
                button = QPushButton('Select File')
                button.clicked.connect(lambda: self.selectController(sr))
                h_layout.addWidget(button)
            
                layout.addLayout(h_layout)

                h_layout = QHBoxLayout()
                button_change = QPushButton('Apply')
                button_change.clicked.connect(lambda: self.changeController(dialog, ip.text(), port.text(), sr.text()))
                button_close = QPushButton('Close')
                button_close.clicked.connect(dialog.reject)
                h_layout.addStretch(1)
                h_layout.addWidget(button_close)
                h_layout.addWidget(button_change)
                layout.addLayout(h_layout)

                # Execute the dialog and wait for the user to close it
                result = dialog.exec()
            
            elif self.nodeSelected.nameClass == "Switch":
                dialog.setMinimumSize((QSize(300, 120)))
                id_label = QLabel("ID: "+str(self.nodeSelected.id), dialog)
                layout.addWidget(id_label)

                numberPortLabel = QLabel("Number of ports: "+str(self.nodeSelected.numberPorts), dialog)
                layout.addWidget(numberPortLabel)

                h_layout = QHBoxLayout()
                button_change = QPushButton('Apply')
                button_change.clicked.connect(dialog.accept)
                button_close = QPushButton('Close')
                button_close.clicked.connect(dialog.reject)
                h_layout.addStretch(1)
                h_layout.addWidget(button_close)
                h_layout.addWidget(button_change)
                layout.addLayout(h_layout)

                # Execute the dialog and wait for the user to close it
                result = dialog.exec()

            else:
                dialog.setMinimumSize((QSize(1000, 600)))
                
                id_label = QLabel("ID: "+str(self.nodeSelected.id), dialog)
                layout.addWidget(id_label)
                
                numberPortLabel = QLabel("Number of ports: "+str(self.nodeSelected.numberPorts), dialog)
                layout.addWidget(numberPortLabel)

                ip_label = QLabel("Set IP:", dialog)
                layout.addWidget(ip_label)
                ip = QLineEdit(dialog)
                ip.setText(self.nodeSelected.ip)
                layout.addWidget(ip)

                mac_label = QLabel("Set MAC:", dialog)
                layout.addWidget(mac_label)
                mac = QLineEdit(dialog)
                mac.setText(self.nodeSelected.mac)
                layout.addWidget(mac)

                h_layout = QHBoxLayout()
                checkbox1 = QCheckBox("Server", self)
                checkbox2 = QCheckBox("Client", self)

                # Set opposite states initially
                if len(self.nodeSelected.command)!=0:
                    checkbox1.setChecked(self.nodeSelected.server)
                    checkbox2.setChecked(not(self.nodeSelected.server))
                else:
                    checkbox1.setChecked(0)
                    checkbox2.setChecked(0)

                # Add checkboxes to the layout
                h_layout.addWidget(checkbox1)
                h_layout.addWidget(checkbox2)
                layout.addLayout(h_layout)

                cmd_label = QLabel("Set command:", dialog)
                layout.addWidget(cmd_label)
                cmd_edit = QPlainTextEdit(dialog)
                cmd_edit.setPlainText(self.nodeSelected.command)
                layout.addWidget(cmd_edit)

                h_layout = QHBoxLayout()
                button_change = QPushButton('Apply')
                button_change.clicked.connect(lambda: self.changeHost(dialog, ip.text(), mac.text(), checkbox1, cmd_edit))
                button_close = QPushButton('Close')
                button_close.clicked.connect(dialog.reject)
                h_layout.addStretch(1)
                h_layout.addWidget(button_close)
                h_layout.addWidget(button_change)
                layout.addLayout(h_layout)

                # Connect the stateChanged signal of each checkbox to a slot
                checkbox1.stateChanged.connect(lambda: self.updateCheckbox2(checkbox1, checkbox2, cmd_edit))
                checkbox2.stateChanged.connect(lambda: self.updateCheckbox1(checkbox1, checkbox2, cmd_edit))

                # Execute the dialog and wait for the user to close it
                result = dialog.exec()
                    
    def updateCheckbox1(self, checkbox1, checkbox2, cmd_edit):
        ryu_name = self.fileNameRyu.rsplit('_', 1)[-1].split('.')[0]
        # Update checkbox1 state based on checkbox2
        if checkbox2.isChecked()==True:
            checkbox1.setChecked(False)
            cmd_edit.setPlainText('#!/bin/bash\niperf3 -c 10.0.0.? -p 5000 -t 20 -i 1 -u -b 1M -P 1 -J > result/client_{0}_{1}.json &\nwait'.format(self.nodeSelected.name, ryu_name)) #iperf3
            # cmd_edit.setPlainText('#!/bin/bash\nITGSend -a 10.0.0.? -rp 9500 -C 100 -c 500 -t 20000 -l ./result/client_{0}_{1}.log &\nwait'.format(self.nodeSelected.name, ryu_name)) # D-ITG
        if checkbox1.isChecked()==False and checkbox2.isChecked()==False:
            cmd_edit.setPlainText('')

    def updateCheckbox2(self, checkbox1, checkbox2, cmd_edit):
        ryu_name = self.fileNameRyu.rsplit('_', 1)[-1].split('.')[0]
        # Update checkbox2 state based on checkbox1
        if checkbox1.isChecked()==True:
            checkbox2.setChecked(False)
            cmd_edit.setPlainText('#!/bin/bash\niperf3 -s -p 5000 -1 -J > result/server_{0}_{1}.json &\nwait'.format(self.nodeSelected.name, ryu_name)) #iperf3
            # cmd_edit.setPlainText('#!/bin/bash\nITGRecv -l ./result/server_{0}_{1}.log &\nwait'.format(self.nodeSelected.name, ryu_name)) # D-ITG
        if checkbox1.isChecked()==False and checkbox2.isChecked()==False:
            cmd_edit.setPlainText('')
    
    def changeHost(self, dialog, ip, mac, checkbox1, cmd_edit):
            # Here you would validate and then update the delay for the link
            try:
                if self.is_valid_ipv4(ip) and self.is_valid_mac_address(mac):
                    self.nodeSelected.ip = ip
                    self.nodeSelected.mac = mac
                else:
                    raise ValueError("Invalid IP or MAC address format.")
                self.nodeSelected.server = int(checkbox1.isChecked())
                self.nodeSelected.command = cmd_edit.toPlainText()
                self.update()
                dialog.reject()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Check type of input.")

    def is_valid_mac_address(self, mac_address):
        pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return bool(pattern.match(mac_address))

    def is_valid_ipv4(self, ip):
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            number = int(part)
            if number < 0 or number > 255:
                return False
        return True
    
    def selectController(self, sr):
        # Open the file dialog and capture the selected file path
        fileName, _ = QFileDialog.getOpenFileName(self, "Select File", "ryu_controller/")
        self.fileNameRyu = fileName
        if self.fileNameRyu:
            sr.setText(self.fileNameRyu)
    
    def changeController(self, dialog, ip, port, sr):
        # Here you would validate and then update the delay for the link
        try:
            if self.is_valid_ipv4(ip):
                    self.nodeSelected.ip = ip
            else:
                raise ValueError("Invalid IP format.")
            self.nodeSelected.port = int(port)
            self.nodeSelected.script = sr
            self.fileNameRyu = sr
            ryu_name = f"_{self.fileNameRyu.rsplit('_', 1)[-1].split('.')[0]}."
            for host in self.hosts:
                cmd = host.command
                pattern = r"(_[^_.]*\.)"
                replacement = ryu_name
                new_string = re.sub(pattern, replacement, cmd)
                host.command = new_string
            self.update()
            dialog.reject()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Check type of input.")
        
    def deleteNodes(self):
        for node in self.selectedNodes:
            if node in self.controllers:
                self.controllers.remove(node)
            elif node in self.switches:
                self.switches.remove(node)
            elif node in self.hosts:
                self.hosts.remove(node)
            if node in self.labels:
                self.labels.remove(node)
            # Now remove all links associated with this node
            to_remove = [link for link in self.links if link.startNode == node or link.endNode == node]
            for link in to_remove:
                self.deleteSelectedLink(link)
            del to_remove
            node.deleteLater()

        self.selectedNodes = []
        # Update the view
        self.update()
    
    def deleteSelectedLink(self, link):
        # Remove the link from the UI and from the links list
        for lk in self.links:
            if link.startNode.id == lk.startNode.id and lk.port[0] > link.port[0] and link.startNode.nameClass == lk.startNode.nameClass:
                lk.port[0] -= 1
            if link.startNode.id == lk.endNode.id and lk.port[1] > link.port[0] and link.startNode.nameClass == lk.endNode.nameClass:
                lk.port[1] -= 1
            if link.endNode.id == lk.startNode.id and lk.port[0] > link.port[1] and link.endNode.nameClass == lk.startNode.nameClass:
                lk.port[0] -= 1
            if link.endNode.id == lk.endNode.id and lk.port[1] > link.port[1] and link.endNode.nameClass == lk.endNode.nameClass:
                lk.port[1] -= 1
        link.startNode.numberPorts -= 1
        link.endNode.numberPorts -= 1
        
        self.links.remove(link)
        self.linksToPaint = []
        self.linksPainted = []
        self.linkSelected = None
        self.update()  # Redraw the UI

    def paintEvent(self, event):
        super().paintEvent(event)
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setFont(self.font)
        
        for contr in self.controllers:
            for sw in self.switches:
                start_pos = contr.center
                end_pos = sw.center
                qp.setPen(QPen(Qt.blue, 1.5, Qt.DotLine))
                qp.drawLine(QPoint(*start_pos), QPoint(*end_pos))
        
        self.linksPainted = []
        if len(self.linksToPaint) != 0 and self.n_paths != -1:
            for i in range(len(self.linksToPaint[self.n_paths])):
                for link in self.linksToPaint[self.n_paths][i]:
                    if link not in self.linksPainted:
                        self.linksPainted.append(link)
    
            for lk in self.linksPainted:
                paths_lk = []
                for i in range(len(self.linksToPaint[self.n_paths])):
                    if lk in self.linksToPaint[self.n_paths][i]:
                        paths_lk.append(i)
                self.drawLinkToPaint(qp, lk, paths_lk)
            
            for link in self.linksHost[self.n_paths]:
                qp.setPen(QPen(Qt.black, 4, Qt.DashLine))
                self.drawLink(qp, link)

            for link in self.links:
                if link not in self.linksPainted and link not in self.linksHost[self.n_paths]:
                    qp.setPen(QPen(Qt.black, 2))
                    self.drawLink(qp, link)
        else:
            for link in self.links:
                if link not in self.linksPainted:
                    qp.setPen(QPen(Qt.black, 2))
                    self.drawLink(qp, link)

        for controller in self.controllers:
            self.drawNodeInfo(qp, controller)

        # Draw nameClass and ID for each switch
        for switch in self.switches:
            self.drawNodeInfo(qp, switch)

        # Draw nameClass and ID for each host
        for host in self.hosts:
            self.drawNodeInfo(qp, host)
                
    def drawLink(self, qp, link):
        fm = QFontMetrics(self.font)
        qp.setFont(self.font)
        startNode = link.startNode
        endNode = link.endNode
        start_pos = startNode.center
        end_pos = endNode.center
        if startNode.nameClass not in ("Controller", "Host") and endNode.nameClass not in ("Controller", "Host"):
            qp.drawLine(QPoint(*start_pos), QPoint(*end_pos))
            cur_metric = None
            if self.dynamic_metric.metric_show == 'delay':
                cur_metric = str(link.delay) + " ms"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'bw':
                cur_metric = str(link.bw) + " Mbps"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'loss':
                cur_metric = str(link.loss) + "%"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'bw, delay':
                fm_2 = QFontMetrics(QFont('Arial', 12))
                cur_metric = str(link.bw) + " Mbps,\n" + str(link.delay) + " ms"
                cur_metric_1 = str(link.bw) + " Mbps,"
                text_width = fm_2.width(cur_metric_1)
                text_height = fm_2.height()


            # Find the midpoint of the line
            mid_point = ((start_pos[0] + end_pos[0]) / 2, (start_pos[1] + end_pos[1]) / 2)

            # Optionally, you can add a background for the delay text for better readability
            
            qp.setBrush(Qt.white)
            qp.setPen(Qt.NoPen)
            if self.dynamic_metric.metric_show == 'bw, delay':
                qp.setFont(QFont('Arial', 12))
                lines = cur_metric.splitlines()
                qp.drawRect(int(mid_point[0] - text_width / 2),
                        int(mid_point[1] - text_height*len(lines) / 2),
                        text_width,
                        text_height*len(lines))
                qp.setPen(QPen(Qt.black, 2))
                for i, line in enumerate(lines):
                    y_offset = text_height * i
                    qp.drawText(int(QPointF(*mid_point).x() - text_width / 2 + text_width*i / 4), int(QPointF(*mid_point).y() - text_height / (3*len(lines))) + y_offset, line)
            else:
                qp.setFont(self.font)
                qp.drawRect(int(mid_point[0] - text_width / 2),
                        int(mid_point[1] - text_height / 2),
                        text_width,
                        text_height)
                qp.setPen(QPen(Qt.black, 2))
                qp.drawText(int(QPointF(*mid_point).x() - text_width / 2), int(QPointF(*mid_point).y() + text_height / 4), cur_metric)
        elif startNode.nameClass == "Host" or endNode.nameClass == "Host":
            qp.drawLine(QPoint(*start_pos), QPoint(*end_pos))

    def drawLinkToPaint(self, qp, link, paths_lk):
        distance = 8
        line_width = 3
        fm = QFontMetrics(self.font)
        qp.setFont(self.font)
        startNode = link.startNode
        endNode = link.endNode
        start_pos = startNode.center
        end_pos = endNode.center
        if startNode.nameClass!="Controller" and endNode.nameClass!="Controller":
            dir_vector = (end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
            norm = (dir_vector[0]**2 + dir_vector[1]**2)**0.5
            if norm != 0:
                unit_vector = (dir_vector[0]/norm, dir_vector[1]/norm)
                
                # Calculate perpendicular vector
                perp_vector = (-unit_vector[1], unit_vector[0])
                n = len(paths_lk)
                if n%2 == 0:
                    for i in range(len(paths_lk)):
                        qp.setPen(QPen(self.colors[paths_lk[i]], line_width))
                        if i < n/2:
                            # Calculate end points of the perpendicular line
                            perp_start = (int(start_pos[0] + perp_vector[0] * (distance*(i+0.5))), int(start_pos[1] + perp_vector[1] * (distance*(i+0.5))))
                            perp_end = (int(end_pos[0] + perp_vector[0] * (distance*(i+0.5))), int(end_pos[1] + perp_vector[1] * (distance*(i+0.5))))

                            # Draw perpendicular line
                            qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
                        else:
                            perp_start = (int(start_pos[0] - perp_vector[0] * (distance*(i-n/2+0.5))), int(start_pos[1] - perp_vector[1] * (distance*(i-n/2+0.5))))
                            perp_end = (int(end_pos[0] - perp_vector[0] * (distance*(i-n/2+0.5))), int(end_pos[1] - perp_vector[1] * (distance*(i-n/2+0.5))))

                            # Draw perpendicular line
                            qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
                else:
                    qp.setPen(QPen(self.colors[paths_lk[0]], line_width))
                    perp_start = (start_pos[0], start_pos[1])
                    perp_end = (end_pos[0], end_pos[1])

                    # Draw perpendicular line
                    qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
                    t = int(n/2)
                    for i in range(1, len(paths_lk)):
                        qp.setPen(QPen(self.colors[paths_lk[i]], line_width))
                        if i <= t:
                            # Calculate end points of the perpendicular line
                            perp_start = (int(start_pos[0] + perp_vector[0] * (distance*i + 1)), int(start_pos[1] + perp_vector[1] * (distance*i + 1)))
                            perp_end = (int(end_pos[0] + perp_vector[0] * (distance*i + 1)), int(end_pos[1] + perp_vector[1] * (distance*i + 1)))

                            # Draw perpendicular line
                            qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
                        else:
                            perp_start = (int(start_pos[0] - perp_vector[0] * distance*(i-t)), int(start_pos[1] - perp_vector[1] * distance*(i-t)))
                            perp_end = (int(end_pos[0] - perp_vector[0] * distance*(i-t)), int(end_pos[1] - perp_vector[1] * distance*(i-t)))

                            # Draw perpendicular line
                            qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
            cur_metric = None
            if self.dynamic_metric.metric_show == 'delay':
                cur_metric = str(link.delay) + " ms"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'bw':
                cur_metric = str(link.bw) + " Mbps"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'loss':
                cur_metric = str(link.loss) + "%"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'bw, delay':
                fm_2 = QFontMetrics(QFont('Arial', 12))
                cur_metric = str(link.bw) + " Mbps,\n" + str(link.delay) + " ms"
                cur_metric_1 = str(link.bw) + " Mbps,"
                text_width = fm_2.width(cur_metric_1)
                text_height = fm_2.height()

            # Find the midpoint of the line
            mid_point = ((start_pos[0] + end_pos[0]) / 2, (start_pos[1] + end_pos[1]) / 2)

            # Optionally, you can add a background for the delay text for better readability
            
            qp.setBrush(Qt.white)
            qp.setPen(Qt.NoPen)
            if self.dynamic_metric.metric_show == 'bw, delay':
                qp.setFont(QFont('Arial', 12))
                lines = cur_metric.splitlines()
                qp.drawRect(int(mid_point[0] - text_width / 2),
                        int(mid_point[1] - text_height*len(lines) / 2),
                        text_width,
                        text_height*len(lines))
                qp.setPen(QPen(Qt.black, 2))
                for i, line in enumerate(lines):
                    y_offset = text_height * i
                    qp.drawText(int(QPointF(*mid_point).x() - text_width / 2 + text_width*i / 4), int(QPointF(*mid_point).y() - text_height / (3*len(lines))) + y_offset, line)
            else:
                qp.setFont(self.font)
                qp.drawRect(int(mid_point[0] - text_width / 2),
                        int(mid_point[1] - text_height / 2),
                        text_width,
                        text_height)
                qp.setPen(QPen(Qt.black, 2))
                qp.drawText(int(QPointF(*mid_point).x() - text_width / 2), int(QPointF(*mid_point).y() + text_height / 4), cur_metric)
        elif startNode.nameClass == "Host" or endNode.nameClass == "Host":
            qp.drawLine(QPoint(*start_pos), QPoint(*end_pos))

    def drawNodeInfo(self, qp, node):
        # The text you want to draw
        node_info = node.name

        # Set font metrics to calculate text width and height
        fm = QFontMetrics(self.font)
        text_width = fm.width(node_info)
        text_height = fm.height()

        rect_width = text_width 
        rect_height = text_height

        rect_x = node.center[0] - rect_width // 2
        rect_y = node.center[1] - 2*rect_height - 5

        # Set the color and draw the background rectangle
        qp.setBrush(Qt.white)  # Background color for the text
        qp.setPen(Qt.NoPen)    # No border for the rectangle
        qp.drawRect(rect_x, rect_y, rect_width, rect_height)

        # Set the pen for the text and draw the text
        # Set text color based on node type for visibility
        if node.nameClass == "Controller":
            qp.setPen(QColor("blue"))
        elif node.nameClass == "Switch":
            qp.setPen(QColor("red"))
        else:  # Host
            qp.setPen(QColor("green"))
        qp.setFont(self.font)
        qp.drawText(QRect(rect_x, rect_y, text_width, text_height), Qt.AlignCenter, node_info)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
