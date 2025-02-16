import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import random
import json
from values import *
from make_plot import makePlotChart
import subprocess
import time
import requests
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
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.text_terminal = QPlainTextEdit(self.central_widget)
        layout = QVBoxLayout()
        layout.addWidget(self.text_terminal)
        self.central_widget.setLayout(layout)
    
    def closeEvent(self, event):
        # self.metric_show = 'bw, delay'
        self.closed.emit()
        super().closeEvent(event)

    def showEvent(self, event):
        # self.metric_show = 'bw, delay'
        pass

class DynamicMetric(QMainWindow):

    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Dynamic Metric')
        self.setGeometry(1200, 100, 500, 500)
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_1 = QWidget()
        self.tab_2 = QWidget()
        self.tab_3 = QWidget()

        self.tabs.addTab(self.tab_1, "Throughput (Mbps)")
        self.tabs.addTab(self.tab_2, "Latency (ms)")
        self.tabs.addTab(self.tab_3, "Cost")

        self.tab_1UI()
        self.tab_2UI()
        self.tab_3UI()

        # self.tabs.currentChanged.connect(self.onTabChanged)
        
        self.metric_show = 'bw, delay'
        # self.index_tab = 0

    def tab_1UI(self):
        self.layout_1 = QVBoxLayout()
        self.table_widget_1 = QTableWidget()
        self.layout_1.addWidget(self.table_widget_1)
        self.tab_1.setLayout(self.layout_1)
        self.tab_1.setFont(QFont('Arial', 15))


    def tab_2UI(self):       
        self.layout_2 = QVBoxLayout()
        self.table_widget_2 = QTableWidget()
        self.layout_2.addWidget(self.table_widget_2)
        self.tab_2.setLayout(self.layout_2)
        self.tab_2.setFont(QFont('Arial', 15))

    def tab_3UI(self):       
        self.layout_3 = QVBoxLayout()
        self.table_widget_3 = QTableWidget()
        self.layout_3.addWidget(self.table_widget_3)
        self.tab_3.setLayout(self.layout_3)
        self.tab_3.setFont(QFont('Arial', 15))
    
    def closeEvent(self, event):
        # self.metric_show = 'bw, delay'
        self.closed.emit()
        super().closeEvent(event)

    def showEvent(self, event):
        self.tabs.setCurrentIndex(0)
        # self.metric_show = 'bw, delay'

    # def onTabChanged(self, index):
    #     self.index_tab = index
    #     if self.index_tab == 0:
    #         self.metric_show = 'dynamic_delay'
    #     elif self.index_tab == 1:
    #         self.metric_show = 'dynamic_bw'

class Controller(QLabel):
    def __init__(self, parent=None):
        super(Controller, self).__init__(parent)
        self.name_class = "Controller"
        self.name = "C"
        self.id = None
        self.ip = '127.0.0.'
        self.port = 6652
        self.center = None
        self.script = None
    
    def toDict(self):
        return {
            'name_class': self.name_class,
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
        self.name_class = "Switch"
        self.name = "S"
        self.id = None
        self.center = None
        self.number_ports = 0
    
    def toDict(self):
        return {
            'name_class': self.name_class,
            'name': self.name,
            'id': self.id,
            'center': self.center,
            'number_ports': self.number_ports
        }

class Host(QLabel):
    def __init__(self, parent=None):
        super(Host, self).__init__(parent)
        self.name_class = "Host"
        self.name = "H"
        self.id = None
        self.ip = '10.0.0.'
        self.mac = '00:00:00:00:00:'
        self.number_ports = 0
        self.center = None
        self.is_server = 1
        self.command = ''
    
    def toDict(self):
        return {
            'name_class': self.name_class,
            'name': self.name,
            'id': self.id,
            'ip': self.ip,
            'mac': self.mac,
            'number_ports': self.number_ports,
            'center': self.center,
            'is_server': self.is_server,
            'command': self.command
        }

class Link:
    def __init__(self):
        self.id = None
        self.start_node = None
        self.end_node = None
        self.port = None
        self.bw = None
        self.delay = None
        self.loss = None
        self.cost = None
    
    def toDict(self):
        return {
            'id': self.id,
            'start_node': self.start_node.toDict(),
            'end_node': self.end_node.toDict(),
            'port': self.port,
            'bw': self.bw,
            'delay': self.delay,
            'loss': self.loss,
            'cost': self.cost
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
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        v_layout = QVBoxLayout(self.central_widget)
        h_layout = QHBoxLayout()
        self.name_topo = QLabel("new.json")
        self.name_topo.setAlignment(Qt.AlignCenter)
        h_layout.addStretch(1)
        h_layout.addWidget(self.name_topo)
        h_layout.addStretch(1)
        v_layout.addLayout(h_layout)
        v_layout.addStretch(1)

        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('File')
        component_menu = menu_bar.addMenu('Component')
        edit_menu = menu_bar.addMenu('Edit')
        action_menu = menu_bar.addMenu('Action')

        file_menu.addAction(self.addOpenAction("images/open.png", "Open"))
        file_menu.addAction(self.addNewAction("images/new.png", "New"))
        file_menu.addAction(self.addSaveAction("images/save.png", "Save"))
        file_menu.addAction(self.addSaveAsAction("images/save_as.png", "Save As"))
        file_menu.addSeparator()
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(qApp.quit)
        file_menu.addAction(exit_action)

        component_menu.addAction(self.addControllerAction("images/controller.png", "Controller"))
        component_menu.addAction(self.addSwitchAction("images/switch.png", "Switch"))
        component_menu.addAction(self.addHostAction("images/host.png", "Host"))
        component_menu.addAction(self.addLinkAction("images/link.png", "Link"))

        edit_menu.addAction(self.addPointerAction("images/pointer.png", "Pointer"))
        edit_menu.addAction(self.addVerticalAction("images/vertical.png", "Vertical"))
        edit_menu.addAction(self.addHorizontalAction("images/horizontal.png", "Horizontal"))
        edit_menu.addAction(self.addTextAction("images/text.png", "Text"))
        edit_menu.addAction(self.addRandomAction("images/random.png", "Random"))

        action_menu.addAction(self.addStartAction("images/start.png", "Start"))
        action_menu.addAction(self.addStopAction("images/stop.png", "Stop"))
        action_menu.addAction(self.addMonitorAction("images/table.png", "Dynamic Metric"))
        action_menu.addAction(self.addPlotAction("images/plot.png", "Plot Result"))
        action_menu.addAction(self.addPathsAction("images/paths.png", "Paths"))
        action_menu.addAction(self.addTerminalAction("images/terminal.png", "Terminal"))

        self.checkbox_bw = QAction("Show bandwidth")
        self.checkbox_delay = QAction("Show delay")
        self.checkbox_cost = QAction("Show cost")
        self.checkbox_bw_delay = QAction("Show bandwidth and delay")

        self.checkbox_bw.setCheckable(True)
        self.checkbox_delay.setCheckable(True)
        self.checkbox_cost.setCheckable(True)
        self.checkbox_bw_delay.setCheckable(True)
        self.checkbox_bw_delay.setChecked(True)

        self.checkbox_bw.triggered.connect(self.handleCheckbox)
        self.checkbox_delay.triggered.connect(self.handleCheckbox)
        self.checkbox_cost.triggered.connect(self.handleCheckbox)
        self.checkbox_bw_delay.triggered.connect(self.handleCheckbox)

        action_menu.addAction(self.checkbox_bw)
        action_menu.addAction(self.checkbox_delay)
        action_menu.addAction(self.checkbox_cost)
        action_menu.addAction(self.checkbox_bw_delay)
        

        # Left Toolbar
        self.toolbar_left = QToolBar("Design Toolbar", self)
        self.toolbar_left.setIconSize(QSize(60, 60))
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar_left)
        self.toolbar_left.addAction(self.addControllerAction("images/controller.png", "Controller"))
        self.toolbar_left.addAction(self.addSwitchAction("images/switch.png", "Switch"))
        self.toolbar_left.addAction(self.addHostAction("images/host.png", "Host"))
        self.toolbar_left.addAction(self.addLinkAction("images/link.png", "Link"))
        self.toolbar_left.addAction(self.addPointerAction("images/pointer.png", "Pointer"))
        self.toolbar_left.addAction(self.addVerticalAction("images/vertical.png", "Vertical"))
        self.toolbar_left.addAction(self.addHorizontalAction("images/horizontal.png", "Horizontal"))
        self.toolbar_left.addAction(self.addTextAction("images/text.png", "Text"))
        self.toolbar_left.addAction(self.addRandomAction("images/random.png", "Random"))
        

        # Right Toolbar
        self.toolbar_right = QToolBar("File Toolbar", self)
        self.toolbar_right.setIconSize(QSize(60, 60))
        self.addToolBar(Qt.RightToolBarArea, self.toolbar_right)
        self.toolbar_right.addAction(self.addOpenAction("images/open.png", "Open"))
        self.toolbar_right.addAction(self.addNewAction("images/new.png", "New"))
        self.toolbar_right.addAction(self.addSaveAction("images/save.png", "Save"))
        self.toolbar_right.addAction(self.addSaveAsAction("images/save_as.png", "Save As"))
        self.toolbar_right.addAction(self.addStartAction("images/start.png", "Start"))
        self.toolbar_right.addAction(self.addStopAction("images/stop.png", "Stop"))
        self.toolbar_right.addAction(self.addMonitorAction("images/table.png", "Dynamic Metrics"))
        self.toolbar_right.addAction(self.addPlotAction("images/plot.png", "Plot Result"))
        self.toolbar_right.addAction(self.addPathsAction("images/paths.png", "Paths"))
        self.toolbar_right.addAction(self.addTerminalAction("images/terminal.png", "Terminal"))
        
        
        self.file_name = None

        self.image_path = None
        self.action_text = "Pointer"
        self.pixmap = None

        self.last_mouse_position = None
        self.text_to_add = None

        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
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
        self.links_to_paint = []
        self.links_painted = []
        self.links_host = []
        self.selected_nodes = []
        self.labels = []
        self.timer = QTimer(self)
        self.mininet_process = None
        self.ryu_process = None
        self.dynamic_metric = DynamicMetric()
        self.dynamic_metric.closed.connect(self.update)
        self.terminal = Terminal()
        self.terminal.closed.connect(self.update)
        self.check_to_open = True
        self.n_paths = 0
        self.node_selected = None
        self.link_selected = None
        self.file_name_mininet = None
        self.file_name_mininet_to_run = None
        self.file_name_ryu = None
    
    def handleCheckbox(self):
        sender = self.sender()
        for checkbox in [self.checkbox_bw, self.checkbox_delay, self.checkbox_cost, self.checkbox_bw_delay]:
            if checkbox != sender:
                checkbox.setChecked(False)
        if self.checkbox_bw.isChecked():
            self.dynamic_metric.metric_show = 'bw'
        elif self.checkbox_delay.isChecked():
            self.dynamic_metric.metric_show = 'delay'
        elif self.checkbox_cost.isChecked():
            self.dynamic_metric.metric_show = 'cost'
        elif self.checkbox_bw_delay.isChecked():
            self.dynamic_metric.metric_show = 'bw, delay'
        else:
            self.dynamic_metric.metric_show = 'bw, delay'
        self.update()
    
    def closeEvent(self, event):
        self.dynamic_metric.close()
        self.terminal.close()

    # LEFT TOOLBAR
    def addControllerAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, action_text))
        return action
    
    def addSwitchAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, action_text))
        return action
    
    def addHostAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, action_text))
        return action

    def addLinkAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, action_text))
        return action

    def addPointerAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, action_text))
        return action
    
    def addVerticalAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(lambda: self.selectedMode(iconPath, "Pointer"))
        action.triggered.connect(self.vertical)
        return action

    def addHorizontalAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(lambda: self.selectedMode(iconPath, "Pointer"))
        action.triggered.connect(self.horizontal)
        return action

    def addRandomAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.setCheckable(True)
        action.triggered.connect(lambda: self.setActive(action))
        action.triggered.connect(lambda: self.selectedMode(iconPath, action_text))
        action.triggered.connect(self.makeRandom)
        return action
    
    def addTextAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
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
        for act in self.toolbar_left.actions():
            act.setChecked(False)
        action.setChecked(True)
        if action.text() != "Text":
            if self.text_to_add != None:
                self.text_to_add.deleteLater()
                self.text_to_add = None
    
    def selectedMode(self, image_path, action_text):
        if len(self.link_link) % 2 == 1:
            self.link_link.pop()
        if action_text in ("Pointer", "Link", "Text", "Random"):
            self.image_path = None
            self.action_text = action_text
            self.pixmap = None
        else:
            self.image_path = image_path
            self.action_text = action_text
            if self.image_path:
                self.pixmap = QPixmap(self.image_path).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                self.pixmap = None
    
    def cancel(self):
        for label in self.selected_nodes:
            label.setStyleSheet("""
                                    QLabel {
                                        font-family: 'Arial';
                                        font-size: 15pt;
                                            }
                                    """)
        self.selected_nodes = []
    
    def vertical(self):
        if self.text_to_add != None:
                self.text_to_add.deleteLater()
                self.text_to_add = None
        for act in self.toolbar_left.actions():
            act.setChecked(False)
        action_pointer = self.getAction(self.toolbar_left, "Pointer")
        action_pointer.setChecked(True)
        if len(self.selected_nodes)!= 0:
            x = 0
            for label in self.selected_nodes:
                x += label.x()
            x_tb = int(x/len(self.selected_nodes))
            for label in self.selected_nodes:
                y = label.y()
                label.move(x_tb, y)
                self.updateNodePosition(label)
            self.cancel()
            self.update()
    
    def horizontal(self):
        if self.text_to_add != None:
                self.text_to_add.deleteLater()
                self.text_to_add = None
        for act in self.toolbar_left.actions():
            act.setChecked(False)
        action_pointer = self.getAction(self.toolbar_left, "Pointer")
        action_pointer.setChecked(True)
        if len(self.selected_nodes)!= 0:
            y = 0
            for label in self.selected_nodes:
                y += label.y()
            y_tb = int(y/len(self.selected_nodes))
            for label in self.selected_nodes:
                x = label.x()
                label.move(x, y_tb)
                self.updateNodePosition(label)
            self.cancel()
            self.update()
    
    def makeRandom(self):
        for link in self.links:
            if isinstance(link.start_node, Host) or isinstance(link.end_node, Host):
                link.delay = random.choice(values_delay_host)
                link.bw = random.choice(values_bw_host)
                link.loss = random.choice(values_loss)
                link.cost = random.choice(values_cost_host)
            else:
                link.delay = random.choice(values_delay)
                link.bw = random.choice(values_bw)
                link.loss = random.choice(values_loss)
                link.cost = random.choice(values_cost)
        self.update()
    
    def placeText(self):
        text = self.text_to_add.text()
        label = QLabel(text, self)
        label.adjustSize()
        label.move(self.text_to_add.pos())
        label.show()
        self.labels.append(label)
        self.text_to_add.deleteLater()
        self.text_to_add = None

    def addTextAtPosition(self, event):
        position = event.pos()
        self.text_to_add.move(position)
        self.text_to_add.show()
        self.text_to_add.setFocus()
    
    # RIGHT TOOLBAR
    def addOpenAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.openTopo)
        return action

    def addNewAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.New)
        return action
    
    def addSaveAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.Save)
        return action

    def addSaveAsAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.saveAs)
        return action

    def addStartAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.start)
        return action

    def addStopAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.Stop)
        return action

    def addPlotAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.plotChart)
        return action

    def addMonitorAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self) 
        action.triggered.connect(self.monitor)
        return action

    def addPathsAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.change_n_paths)
        return action

    def addTerminalAction(self, iconPath, action_text):
        action = QAction(QIcon(iconPath), action_text, self)
        action.triggered.connect(self.showTerminal)
        return action

    def change_n_paths(self):
        if self.n_paths < (len(self.links_to_paint)-1):
            self.n_paths += 1
        else:
            self.n_paths = -1
        self.update()

    def showTerminal(self):
        self.terminal.show()
        self.update()

    def monitor(self):
        self.dynamic_metric.show()
        self.update()
    
    def openTopo(self):
        options = QFileDialog.Options()
        self.file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "topo_mininet/", "JSON Files (*.json);;All Files (*)", options=options)
        if self.file_name:
            self.refreshSpace()
            self.initParameters()
            self.loadTopo(self.file_name)
            self.name_topo.setText(os.path.basename(self.file_name))
            base_name = os.path.splitext(self.file_name)[0]
            self.file_name_mininet = f'{base_name}.py'
            self.makeScriptIperf3()
        self.selectedMode("images/pointer.png", "Pointer")
        for act in self.toolbar_left.actions():
            act.setChecked(False)
        action_pointer = self.getAction(self.toolbar_left, "Pointer")
        action_pointer.setChecked(True)
        self.n_controllers += len(self.controllers)
        self.n_switches += len(self.switches)
        self.n_hosts += len(self.hosts)
        self.n_links += len(self.links)

    def refreshSpace(self):
        for item in self.controllers+self.hosts+self.switches+self.labels:
            item.deleteLater()
            item = None
        self.update()
    
    def loadTopo(self, file_name):
        try:
            with open(file_name, 'r') as file:
                topo_data = json.load(file)
                self.getInfo(topo_data)
                self.update()
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Failed to open the topology: {e}")
    
    def getInfo(self, topo_data):
        for item in topo_data['controllers']:
            new_node = self.loadNode("Controller", item)
            self.nodeDraw(new_node)
            self.controllers.append(new_node)

        for item in topo_data['hosts']:
            new_node = self.loadNode("Host", item)
            self.nodeDraw(new_node)
            self.hosts.append(new_node)

        for item in topo_data['switches']:
            new_node = self.loadNode("Switch", item)
            self.nodeDraw(new_node)
            self.switches.append(new_node)
        
        for item in topo_data['labels']:
            text = item['text']
            label = QLabel(text, self)
            label.adjustSize()
            label.move(item['pos'][0], item['pos'][1])
            label.show()
            self.labels.append(label)

        for item in topo_data['links']:
            link = Link()
            link.id = item['id']
            name_class_start = item['start_node']['name_class']
            start_node = self.loadNode(name_class_start, item['start_node'])
            link.start_node = self.getNode(start_node)
            name_class_end = item['end_node']['name_class']
            end_node = self.loadNode(name_class_end, item['end_node'])
            link.end_node = self.getNode(end_node)
            link.delay = item['delay']
            link.bw = item['bw']
            link.loss = item['loss']
            link.cost = item['cost']
            link.port = item['port']
            self.links.append(link)

    def nodeDraw(self, new_node):
        new_node.setPixmap(self.pixmap)
        new_node.setFixedSize(self.pixmap.size())
        x = new_node.center[0] - self.pixmap.width()//2
        y = new_node.center[1] - self.pixmap.height()//2
        new_node.move(x, y)
        new_node.show()

    def getNode(self, start_node):
        if start_node.name_class == "Controller":
            for ctr in self.controllers:
                if ctr.id == start_node.id:
                    return ctr
        elif start_node.name_class == "Switch":
            for ctr in self.switches:
                if ctr.id == start_node.id:
                    return ctr
        else:
            for ctr in self.hosts:
                if ctr.id == start_node.id:
                    return ctr

    def loadNode(self, name_class, item):
        if name_class == "Controller":
            self.selectedMode("images/controller.png", "Controller")
            new_node = Controller(self)
            new_node.id = item['id']
            new_node.center = item['center']
            new_node.name = item['name']
            new_node.ip = item['ip']
            new_node.port = item['port']
            new_node.script = item['script']
            self.file_name_ryu = new_node.script
            return new_node
        elif name_class == "Switch":
            self.selectedMode("images/switch.png", "Switch")
            new_node = Switch(self)
            new_node.id = item['id']
            new_node.center = item['center']
            new_node.name = item['name']
            new_node.number_ports = item['number_ports']
            return new_node
        else:
            self.selectedMode("images/host.png", "Host")
            new_node = Host(self)
            new_node.id = item['id']
            new_node.center = item['center']
            new_node.name = item['name']
            new_node.ip = item['ip']
            new_node.mac = item['mac']
            new_node.number_ports = item['number_ports']
            new_node.is_server = item['is_server']
            new_node.command = item['command']
            return new_node
    
    def New(self):
        self.name_topo.setText("new.json")
        self.file_name = None
        self.refreshSpace()
        self.initParameters()

    def Save(self):
        if self.file_name:
            self.saveTopo()
            base_name = os.path.splitext(self.file_name)[0]
            self.file_name_mininet = f'{base_name}.py'
            self.makeScriptMininet()
            self.makeScriptIperf3()
        else:
            self.saveAs()
    
    def makeTopoJson(self):
        topo_data = {}
        
        topo_data['controllers'] = []
        for ctr in self.controllers:
            topo_data['controllers'].append(ctr.toDict())
        
        topo_data['switches'] = []
        for sw in self.switches:
            topo_data['switches'].append(sw.toDict())
        
        topo_data['hosts'] = []
        for hst in self.hosts:
            topo_data['hosts'].append(hst.toDict())

        topo_data['links'] = []
        for lk in self.links:
            topo_data['links'].append(lk.toDict())

        topo_data['labels'] = []
        for lb in self.labels:
            lb_dict = {}
            lb_dict['text'] = lb.text()
            lb_dict['pos'] = (lb.x(), lb.y())
            topo_data['labels'].append(lb_dict)
        
        topo_json = json.dumps(topo_data, indent=4)
        return topo_json

    def saveAs(self):
        options = QFileDialog.Options()
        default_file_name = "topo_mininet/topology.json"
        self.file_name, _ = QFileDialog.getSaveFileName(self, "Save As Topology", default_file_name, "JSON Files (*.json);;All Files (*)", options=options)

        if self.file_name:
            if not self.file_name.endswith('.json'):
                self.file_name += '.json'
            self.saveTopo()
            self.name_topo.setText(os.path.basename(self.file_name))
            base_name = os.path.splitext(self.file_name)[0]
            self.file_name_mininet = f'{base_name}.py'
            self.makeScriptMininet()
            self.makeScriptIperf3()
            
    def saveTopo(self):
        with open(self.file_name, 'w') as f:
            topoJson = self.makeTopoJson()
            f.write(topoJson)
        f.close()

    def makeScriptIperf3(self):
        for host in self.hosts:
            with open("traffic/{}.sh".format(host.name), 'w') as f:
                f.write(host.command)
            f.close()

    def makeScriptMininet(self):
        try:
            lib_1= self.makeString()
            with open(self.file_name_mininet, 'w') as f:
                f.write(lib_1)
            f.close()
            QMessageBox.information(self, "Save", "Save topology and mininet script successfully!")
        except ValueError:
            QMessageBox.warning(self, "Error", "Can not save topology and mininet script. Check network!")
    
    def makeString(self):
        body_1 = s1

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
            l = "\t\tself.addLink({}, {}, {}, {}, bw={}, delay='{}ms', loss={})\n".format(lk.start_node.name, lk.end_node.name, lk.port[0], lk.port[1], lk.bw, lk.delay, lk.loss)
            link_str = link_str + l

        ctr_str = ""
        for ctr in self.controllers:
            ctr_ = "\tnet = Mininet(topo=topo, controller=RemoteController(name='{}', ip='{}', port={}), link=link)\n".format(ctr.name, ctr.ip, ctr.port)
            ctr_str = ctr_str + ctr_
        ctr_str += "\tnet.start()\n\tsleep(2)\n"

        hs = ""
        for host in self.hosts:
            if host.is_server == 1:
                hs += "\tmakeTerm(net['{}'],cmd='bash traffic/{}.sh')\n".format(host.name, host.name)
        hs += "\tsleep(2)\n"
        for host in self.hosts:
            if host.is_server == 0:
                hs += "\tmakeTerm(net['{}'],cmd='bash traffic/{}.sh')\n".format(host.name, host.name)

        body_1 = body_1 + host_str + sw_str + link_str + s2 + ctr_str + hs + s3
        return body_1
        
    def start(self):
        if self.file_name:
            base_name = os.path.splitext(self.file_name)[0]
            base_name = os.path.basename(base_name)
            options = QFileDialog.Options()
            filter_pattern = f"*{base_name}*.py"
            self.file_name_mininet_to_run, _ = QFileDialog.getOpenFileName(self, "Mininet Script",
                                                                    "topo_mininet/", 
                                                                    f"Python Files ({filter_pattern});;All Files (*)", 
                                                                    options=options)
            if self.file_name_mininet_to_run:
                if self.ryu_process and self.ryu_process.poll() is None:
                    QMessageBox.warning(self, "Ryu controller", "Ryu controller is already running!")
                    return
                if self.mininet_process and self.mininet_process.poll() is None:
                    QMessageBox.warning(self, "Mininet", "Mininet is already running!")
                    return
                try:
                    self.ryu_process = subprocess.Popen(['xterm', '-geometry', '90x40', '-e', "ryu-manager", "--observe-links", self.file_name_ryu], stdout=subprocess.PIPE)
                except ValueError:
                    QMessageBox.warning(self, "Ryu controller", "Can not start Ryu controller!")
                
                time.sleep(2)

                try:
                    self.mininet_process = subprocess.Popen(['xterm', '-geometry', '120x30', '-e', "sudo", "python3", self.file_name_mininet_to_run], stdout=subprocess.PIPE)
                except ValueError:
                    QMessageBox.warning(self, "Mininet", "Can not start Mininet!")

                self.timer.timeout.connect(lambda: self.showMetric(self.dynamic_metric.table_widget_1, 'throughput'))
                self.timer.timeout.connect(lambda: self.showMetric(self.dynamic_metric.table_widget_2, 'latency'))
                self.timer.timeout.connect(lambda: self.showMetric(self.dynamic_metric.table_widget_3, 'cost_2'))
                
                # self.timer.timeout.connect(self.showPaths)
                update_interval = 2000
                self.timer.start(update_interval)
    
    def showPaths(self):
        try:
            response = requests.get("http://localhost:8080/paths")
            if response.status_code == 200:
                paths_dict = response.json()
                if paths_dict != None:
                    if len(paths_dict) != 0:
                        self.links_to_paint = []
                        self.links_host = []
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
                                        if lk.start_node.id in link and lk.end_node.id in link and lk not in pth and lk.start_node.name_class == "Switch" and lk.end_node.name_class == "Switch":
                                            pth.append(lk)
                                            break

                                paths.append(pth)

                                if c:
                                    for lk in self.links:
                                        if (lk.start_node.name_class == "Host" and lk.start_node.ip == pths[3] or lk.end_node.name_class == "Host" and lk.end_node.ip == pths[3]) and lk not in lksHost:
                                            lksHost.append(lk)
                                            continue
                                        if (lk.start_node.name_class == "Host" and lk.start_node.ip == pths[4] or lk.end_node.name_class == "Host" and lk.end_node.ip == pths[4]) and lk not in lksHost:
                                            lksHost.append(lk)
                                            continue
                                c = False

                            for key in range(len(pths[0])):
                                # int_string = 'Path ' + str(key+1) + ': [' + ', '.join(map(str, pths[0][key])) + '], length = ' + str(pths[2][key]) + '\n'
                                int_string = 'Path ' + str(key+1) + ': [' + ', '.join(map(str, pths[0][key])) + ']' + '\n'
                                terminal_string += int_string
                            if len(paths_dict) > 1:
                                side = '\n'
                                terminal_string += side

                            self.links_to_paint.append(paths)
                            self.links_host.append(lksHost)
                        
                        self.terminal.text_terminal.setPlainText(terminal_string)
                        self.terminal.show()
                        self.update()
            else:
                print(f"Error: Received status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
    
    def showMetric(self, table_widget, metric):
        try:
            link_api = "http://localhost:8080/" + metric
            response = requests.get(link_api)
            if response.status_code == 200:
                metrics = response.json()
                if metrics != None:
                    if len(metrics) != 0:
                        table_widget.clearContents()
                        table_widget.setRowCount(len(metrics))
                        table_widget.setColumnCount(len(metrics))
                        c = 0
                        for i in range(len(metrics)):
                            d = True
                            while d:
                                for key, nested in metrics.items():
                                    if int(key) == (i+1+c):
                                        header_item = QTableWidgetItem("S" + key)
                                        table_widget.setHorizontalHeaderItem(i, header_item)
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
                                        table_widget.setVerticalHeaderItem(i, header_item)
                                        d = False
                                        break
                                if d:
                                    c+=1
                        
                        for key, nested in metrics.items():
                            for nestedKey, nestedValue in nested.items():
                                item = QTableWidgetItem(str(nestedValue))
                                item.setTextAlignment(Qt.AlignCenter)

                                for i in range(table_widget.rowCount()):
                                    dk = False
                                    for j in range(table_widget.columnCount()):
                                        if table_widget.verticalHeaderItem(j).text() == ("S" + nestedKey) and table_widget.horizontalHeaderItem(i).text() == ("S" + key):
                                            table_widget.setItem(i, j, item)
                                            dk = True
                                            break
                                    if dk:
                                        break
                        
                        width = table_widget.verticalHeader().width() + 30
                        height = table_widget.horizontalHeader().height() + 60

                        for i in range(table_widget.columnCount()):
                            table_widget.setColumnWidth(i, 60)
                            width += table_widget.columnWidth(i)
                        
                        for i in range(table_widget.rowCount()):
                            height += table_widget.rowHeight(i)
                        self.dynamic_metric.resize(width, height)
                        if self.check_to_open:
                            self.dynamic_metric.show()
                            self.check_to_open = False

                        self.update()

            else:
                print(f"Error: Received status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")

    def Stop(self):
        try:
            if self.ryu_process:
                self.ryu_process.terminate()
                time.sleep(2)
                if self.ryu_process.poll() is None:
                    self.ryu_process.kill()
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
            self.check_to_open = True
            # self.DynamicMetric.metric_show = 'delay'
            # self.links_to_paint = []
            # self.links_host = []
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
            file_names, _ = QFileDialog.getOpenFileNames(self, "Plot result", "result/", "JSON Files (*.json)")
            if file_names:
                try:
                    makePlotChart(file_names)
                    break
                except:
                    continue
            else:
                break

    # EVENT
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.node_selected = self.getNodeAtPosition(event.pos())
        self.link_selected = self.getLinkAtPosition(event.pos())
        self.last_mouse_position = event.pos()
        
        if self.action_text == "Pointer":
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, self.origin))
            self.rubber_band.show()

        if event.button() == Qt.LeftButton:
            if self.node_selected == None and self.action_text == "Pointer":
                self.cancel()
            else:
                self.placeImage(event.pos())
                if self.action_text == "Link":
                    self.prepareLine(self.node_selected)
        elif event.button() == Qt.RightButton and self.node_selected not in self.labels:
            self.checkForMetricRightClick(event.pos())
            self.openNodeDialog()
        
        if self.action_text == "Text":
            if self.text_to_add == None:
                self.text_to_add = QLineEdit(self)
                self.text_to_add.setPlaceholderText("Enter text here")
                self.addTextAtPosition(event)
                self.text_to_add.returnPressed.connect(self.placeText)
            else:
                self.addTextAtPosition(event)
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.origin is not None and self.node_selected == None:
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())
        if self.action_text == "Pointer":
            if len(self.selected_nodes)!=0:
                if self.node_selected in self.selected_nodes:
                    for node in self.selected_nodes:
                        delta = event.pos() - self.last_mouse_position
                        new_pos = node.pos() + delta
                        node.move(new_pos)
                        self.updateNodePosition(node)
            elif self.node_selected != None:
                delta = event.pos() - self.last_mouse_position
                new_pos = self.node_selected.pos() + delta
                self.node_selected.move(new_pos)
                self.updateNodePosition(self.node_selected)
            self.last_mouse_position = event.pos()
        self.update()
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.origin is not None:
            self.rubber_band.hide()
            rect = self.rubber_band.geometry()
            self.selectLabels(rect)
            self.origin = None
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            if self.link_selected:
                self.deleteSelectedLink(self.link_selected)
            if len(self.selected_nodes) != 0:
                self.deleteNodes()
    
    def placeImage(self, position):
        if self.pixmap and not self.pixmap.isNull():
            self.addNode(position)
    
    def addNode(self, position):
        if self.action_text == "Controller":
            new_node = Controller(self)
            self.n_controllers += 1
            list_id_ctr = [item.id for item in self.controllers]
            for i in range(1, self.n_controllers+1):
                if i not in list_id_ctr:
                    new_node.id = i
                    break
            new_node.setPixmap(self.pixmap)
            new_node.setFixedSize(self.pixmap.size())
            x = position.x() - self.pixmap.width()//2
            y = position.y() - self.pixmap.height()//2
            new_node.move(x, y)
            new_node.show()
            new_node.center = (position.x(), position.y())
            new_node.name = new_node.name + str(new_node.id)
            new_node.ip = new_node.ip + str(new_node.id)
            new_node.port = new_node.port + new_node.id
            self.controllers.append(new_node)
        
        elif self.action_text == "Switch":
            new_node = Switch(self)
            self.n_switches += 1
            list_id_sw = [item.id for item in self.switches]
            for i in range(1, self.n_switches+1):
                if i not in list_id_sw:
                    new_node.id = i
                    break
            new_node.setPixmap(self.pixmap)
            new_node.setFixedSize(self.pixmap.size())
            x = position.x() - self.pixmap.width()//2
            y = position.y() - self.pixmap.height()//2
            new_node.move(x, y)
            new_node.show()
            new_node.center = (position.x(), position.y())
            new_node.name = new_node.name + str(new_node.id)
            self.switches.append(new_node)

        elif self.action_text == "Host":
            new_node = Host(self)
            self.n_hosts += 1
            list_id_h = [item.id for item in self.hosts]
            for i in range(1, self.n_hosts+1):
                if i not in list_id_h:
                    new_node.id = i
                    break
            new_node.setPixmap(self.pixmap)
            new_node.setFixedSize(self.pixmap.size())
            x = position.x() - self.pixmap.width()//2
            y = position.y() - self.pixmap.height()//2
            new_node.move(x, y)
            new_node.show()
            new_node.center = (position.x(), position.y())
            new_node.name = new_node.name + str(new_node.id)
            if new_node.id < 10:
                new_node.mac = new_node.mac + '0' + str(new_node.id)
            elif 10 <= new_node.id < 100:
                new_node.mac = new_node.mac + str(new_node.id)
            else:
                QMessageBox.warning(self, "Invalid Input", "Number of hosts is only lower than 100.")
            new_node.ip = new_node.ip + str(new_node.id)
            self.hosts.append(new_node)
        self.update()

    def getNodeAtPosition(self, position):
        for label in self.findChildren(QLabel):
            if label.geometry().contains(position):
                return label
        return None
    
    def getLinkAtPosition(self, position):
        for link in self.links:
            start_node = link.start_node
            end_node = link.end_node
            start_pos = start_node.center
            end_pos = end_node.center
            mid_point = QPoint(int((start_pos[0] + end_pos[0]) / 2), int((start_pos[1] + end_pos[1]) / 2))

            metric_text = str(link.delay)
            text_width = self.fontMetrics().width(metric_text)
            text_height = self.fontMetrics().height()
            text_rect = QRect(int(mid_point.x() - text_width / 2), int(mid_point.y() - text_height / 2),
                            text_width, text_height)

            if text_rect.contains(position):
                return link
        return None
    
    def prepareLine(self, closest_node):
        if closest_node and not(isinstance(closest_node, Controller)) and closest_node not in self.labels:
            if len(self.link_link) % 2 == 1:
                if not(self.link_link[-1] is closest_node):
                    self.link_link.append(closest_node)
                    self.update()
                    
                    link = Link()
                    self.n_links += 1
                    id = self.n_links
                    link.id = id
                    link.start_node = self.link_link[-2]
                    link.end_node = self.link_link[-1]
                    link.start_node.number_ports += 1
                    link.end_node.number_ports += 1
                    link.port = [link.start_node.number_ports, link.end_node.number_ports]
                    if isinstance(link.start_node, Host) or isinstance(link.end_node, Host):
                        link.delay = random.choice(values_delay_host)
                        link.bw = random.choice(values_bw_host)
                        link.loss = random.choice(values_loss)
                        link.cost = random.choice(values_cost_host)
                    else:
                        link.delay = random.choice(values_delay)
                        link.bw = random.choice(values_bw)
                        link.loss = random.choice(values_loss)
                        link.cost = random.choice(values_cost)
                    cond = True
                    for lk in self.links:
                        if set((link.start_node, link.end_node)) == set((lk.start_node, lk.end_node)):
                            cond = False
                    if cond:
                        self.links.append(link)
            else:
                self.link_link.append(closest_node)
    
    def updateNodePosition(self, label):
        x, y = label.x(), label.y()
        center_pos = (x + label.width()//2, y + label.height()//2)
        label.center = center_pos

    def selectLabels(self, rect):
        for label in self.controllers+self.hosts+self.switches+self.labels:
            if rect.intersects(label.geometry()) and label not in self.selected_nodes:
                self.selected_nodes.append(label)
        if len(self.selected_nodes)>0:
            for label in self.selected_nodes:
                label.setStyleSheet("""
                                    QLabel {
                                        border: 2px solid blue;
                                        font-family: 'Arial';
                                        font-size: 15pt;
                                            }
                                    """)

    def checkForMetricRightClick(self, position):
        for link in self.links:
            start_node = link.start_node
            end_node = link.end_node
            start_pos = start_node.center
            end_pos = end_node.center
            mid_point = QPoint(int((start_pos[0] + end_pos[0]) / 2), int((start_pos[1] + end_pos[1]) / 2))

            cur_delay = str(link.delay)
            cur_bw = str(link.bw)
            cur_loss = str(link.loss)
            text_width = self.fontMetrics().width(cur_delay + " ms")
            text_height = self.fontMetrics().height()
            text_rect = QRect(int(mid_point.x() - text_width / 2), int(mid_point.y() - text_height / 2),
                            text_width, text_height)

            if text_rect.contains(position):
                self.openMetricDialog(link, cur_delay, cur_bw, cur_loss)
                break

    def openMetricDialog(self, link, cur_delay, cur_bw, cur_loss):
        dialog = QDialog()
        dialog.setMinimumSize((QSize(400, 250)))
        dialog.setFont(self.font)
        title = f"Configure Metrics for Link: {link.start_node.name} - {link.end_node.name}"
        dialog.setWindowTitle(title)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        bw_label = QLabel("Bandwidth (Mbps):", dialog)
        layout.addWidget(bw_label)
        bw = QLineEdit(dialog)
        bw.setText(cur_bw)
        layout.addWidget(bw)

        delay_label = QLabel("Delay (ms):", dialog)
        layout.addWidget(delay_label)
        delay = QLineEdit(dialog)
        delay.setText(cur_delay)
        layout.addWidget(delay)

        loss_label = QLabel("Packet Loss Rate (%):", dialog)
        layout.addWidget(loss_label)
        loss = QLineEdit(dialog)
        loss.setText(cur_loss)
        layout.addWidget(loss)

        h_layout = QHBoxLayout()
        button_change = QPushButton('Apply')
        button_change.clicked.connect(lambda: self.changeLinkMetric(dialog, link, delay.text(), bw.text(), loss.text()))
        button_close = QPushButton('Cancel')
        button_close.clicked.connect(dialog.reject)
        h_layout.addStretch(1)
        h_layout.addWidget(button_close)
        h_layout.addWidget(button_change)
        layout.addLayout(h_layout)

        result = dialog.exec()

    def changeLinkMetric(self, dialog, link, delay, bw, loss):
        try:
            link.delay = int(delay)
            link.bw = int(bw)
            link.loss = int(loss)
            self.update()
            dialog.reject()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Check type of input.")

    def openNodeDialog(self):
        if self.node_selected:
            dialog = QDialog()
            dialog.setFont(self.font)
            title = f"Configure {self.node_selected.name} Parameters"
            dialog.setWindowTitle(title)

            layout = QVBoxLayout()
            dialog.setLayout(layout)

            if self.node_selected.name_class == "Controller":
                dialog.setMinimumSize((QSize(600, 300)))
                id_label = QLabel(f"Controller ID: {self.node_selected.id}", dialog)
                layout.addWidget(id_label)

                ip_label = QLabel("IP Address:", dialog)
                layout.addWidget(ip_label)
                ip = QLineEdit(dialog)
                ip.setText(self.node_selected.ip)
                layout.addWidget(ip)

                port_label = QLabel("Port Number:", dialog)
                layout.addWidget(port_label)
                port = QLineEdit(dialog)
                port.setText(str(self.node_selected.port))
                layout.addWidget(port)

                sr_label = QLabel("Ryu Script Path:", dialog)
                layout.addWidget(sr_label)
                h_layout = QHBoxLayout()
                sr = QLineEdit(dialog)
                sr.setText(str(self.node_selected.script))
                h_layout.addWidget(sr)
                button = QPushButton('Browse')
                button.clicked.connect(lambda: self.selectController(sr))
                h_layout.addWidget(button)
            
                layout.addLayout(h_layout)

                h_layout = QHBoxLayout()
                button_change = QPushButton('Apply')
                button_change.clicked.connect(lambda: self.changeController(dialog, ip.text(), port.text(), sr.text()))
                button_close = QPushButton('Cancel')
                button_close.clicked.connect(dialog.reject)
                h_layout.addStretch(1)
                h_layout.addWidget(button_close)
                h_layout.addWidget(button_change)
                layout.addLayout(h_layout)

                result = dialog.exec()
            
            elif self.node_selected.name_class == "Switch":
                dialog.setMinimumSize((QSize(300, 120)))
                id_label = QLabel(f"Switch ID: {self.node_selected.id}", dialog)
                layout.addWidget(id_label)

                port_count_label = QLabel(f"Number of Ports: {self.node_selected.number_ports}", dialog)
                layout.addWidget(port_count_label)

                h_layout = QHBoxLayout()
                button_close = QPushButton('Cancel')
                button_close.clicked.connect(dialog.reject)
                h_layout.addStretch(1)
                h_layout.addWidget(button_close)
                layout.addLayout(h_layout)

                result = dialog.exec()

            else:
                dialog.setMinimumSize((QSize(1000, 600)))
                
                id_label = QLabel(f"Host ID: {self.node_selected.id}", dialog)
                layout.addWidget(id_label)
                
                port_count_label = QLabel(f"Number of Ports: {self.node_selected.number_ports}", dialog)
                layout.addWidget(port_count_label)

                ip_label = QLabel("IP Address:", dialog)
                layout.addWidget(ip_label)
                ip = QLineEdit(dialog)
                ip.setText(self.node_selected.ip)
                layout.addWidget(ip)

                mac_label = QLabel("MAC Address:", dialog)
                layout.addWidget(mac_label)
                mac = QLineEdit(dialog)
                mac.setText(self.node_selected.mac)
                layout.addWidget(mac)

                h_layout = QHBoxLayout()
                checkbox_1 = QCheckBox("Server", self)
                checkbox_2 = QCheckBox("Client", self)

                if len(self.node_selected.command)!=0:
                    checkbox_1.setChecked(self.node_selected.is_server)
                    checkbox_2.setChecked(not(self.node_selected.is_server))
                else:
                    checkbox_1.setChecked(0)
                    checkbox_2.setChecked(0)

                h_layout.addWidget(checkbox_1)
                h_layout.addWidget(checkbox_2)
                layout.addLayout(h_layout)

                cmd_label = QLabel("Iperf3 Bash Script:", dialog)
                layout.addWidget(cmd_label)
                cmd_edit = QPlainTextEdit(dialog)
                cmd_edit.setPlainText(self.node_selected.command)
                layout.addWidget(cmd_edit)

                h_layout = QHBoxLayout()
                button_change = QPushButton('Apply')
                button_change.clicked.connect(lambda: self.changeHost(dialog, ip.text(), mac.text(), checkbox_1, cmd_edit))
                button_close = QPushButton('Cancel')
                button_close.clicked.connect(dialog.reject)
                h_layout.addStretch(1)
                h_layout.addWidget(button_close)
                h_layout.addWidget(button_change)
                layout.addLayout(h_layout)

                checkbox_1.stateChanged.connect(lambda: self.updateCheckbox2(checkbox_1, checkbox_2, cmd_edit))
                checkbox_2.stateChanged.connect(lambda: self.updateCheckbox1(checkbox_1, checkbox_2, cmd_edit))

                result = dialog.exec()
                    
    def updateCheckbox1(self, checkbox_1, checkbox_2, cmd_edit):
        ryu_name = os.path.splitext(self.file_name_ryu)[0]
        ryu_name = os.path.basename(ryu_name)
        if checkbox_2.isChecked()==True:
            checkbox_1.setChecked(False)
            cmd_edit.setPlainText('#!/bin/bash\niperf3 -c 10.0.0.? -p 5000 -t 20 -i 1 -u -b 1M -P 1 -J > result/client/{0}_{1}.json &\nwait'.format(self.node_selected.name, ryu_name)) #iperf3
            # cmd_edit.setPlainText('#!/bin/bash\nITGSend -a 10.0.0.? -rp 9500 -C 100 -c 500 -t 20000 -l ./result/client_{0}_{1}.log &\nwait'.format(self.node_selected.name, ryu_name)) # D-ITG
        if checkbox_1.isChecked()==False and checkbox_2.isChecked()==False:
            cmd_edit.setPlainText('')

    def updateCheckbox2(self, checkbox_1, checkbox_2, cmd_edit):
        ryu_name = os.path.splitext(self.file_name_ryu)[0]
        ryu_name = os.path.basename(ryu_name)
        if checkbox_1.isChecked()==True:
            checkbox_2.setChecked(False)
            cmd_edit.setPlainText('#!/bin/bash\niperf3 -s -p 5000 -1 -J > result/server/{0}_{1}.json &\nwait'.format(self.node_selected.name, ryu_name)) #iperf3
            # cmd_edit.setPlainText('#!/bin/bash\nITGRecv -l ./result/server_{0}_{1}.log &\nwait'.format(self.node_selected.name, ryu_name)) # D-ITG
        if checkbox_1.isChecked()==False and checkbox_2.isChecked()==False:
            cmd_edit.setPlainText('')
    
    def changeHost(self, dialog, ip, mac, checkbox_1, cmd_edit):
            try:
                if self.isValidIpv4(ip) and self.isValidMacAddress(mac):
                    self.node_selected.ip = ip
                    self.node_selected.mac = mac
                else:
                    raise ValueError("Invalid IP or MAC address format.")
                self.node_selected.is_server = int(checkbox_1.isChecked())
                self.node_selected.command = cmd_edit.toPlainText()
                self.update()
                dialog.reject()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Check type of input.")

    def isValidMacAddress(self, mac_address):
        pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return bool(pattern.match(mac_address))

    def isValidIpv4(self, ip):
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
        file_name, _ = QFileDialog.getOpenFileName(self, "Ryu Script", "ryu_controller/")
        self.file_name_ryu = file_name
        if self.file_name_ryu:
            sr.setText(self.file_name_ryu)
    
    def changeController(self, dialog, ip, port, sr):
        try:
            if self.isValidIpv4(ip):
                    self.node_selected.ip = ip
            else:
                raise ValueError("Invalid IP format.")
            self.node_selected.port = int(port)
            self.node_selected.script = sr
            self.file_name_ryu = sr
            ryu_name = os.path.splitext(self.file_name_ryu)[0]
            ryu_name = os.path.basename(ryu_name)
            for host in self.hosts:
                cmd = host.command
                pattern = r'\_.*\.' 
                replacement = f"_{ryu_name}."
                new_string = re.sub(pattern, replacement, cmd)
                host.command = new_string
            self.update()
            dialog.reject()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Check type of input.")
        
    def deleteNodes(self):
        for node in self.selected_nodes:
            if node in self.controllers:
                self.controllers.remove(node)
            elif node in self.switches:
                self.switches.remove(node)
            elif node in self.hosts:
                self.hosts.remove(node)
            if node in self.labels:
                self.labels.remove(node)
            to_remove = [link for link in self.links if link.start_node == node or link.end_node == node]
            for link in to_remove:
                self.deleteSelectedLink(link)
            del to_remove
            node.deleteLater()

        self.selected_nodes = []
        self.update()
    
    def deleteSelectedLink(self, link):
        for lk in self.links:
            if link.start_node.id == lk.start_node.id and lk.port[0] > link.port[0] and link.start_node.name_class == lk.start_node.name_class:
                lk.port[0] -= 1
            if link.start_node.id == lk.end_node.id and lk.port[1] > link.port[0] and link.start_node.name_class == lk.end_node.name_class:
                lk.port[1] -= 1
            if link.end_node.id == lk.start_node.id and lk.port[0] > link.port[1] and link.end_node.name_class == lk.start_node.name_class:
                lk.port[0] -= 1
            if link.end_node.id == lk.end_node.id and lk.port[1] > link.port[1] and link.end_node.name_class == lk.end_node.name_class:
                lk.port[1] -= 1
        link.start_node.number_ports -= 1
        link.end_node.number_ports -= 1
        
        self.links.remove(link)
        self.links_to_paint = []
        self.links_painted = []
        self.link_selected = None
        self.update()

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
        
        self.links_painted = []
        if len(self.links_to_paint) != 0 and self.n_paths != -1:
            for i in range(len(self.links_to_paint[self.n_paths])):
                for link in self.links_to_paint[self.n_paths][i]:
                    if link not in self.links_painted:
                        self.links_painted.append(link)
    
            for lk in self.links_painted:
                paths_lk = []
                for i in range(len(self.links_to_paint[self.n_paths])):
                    if lk in self.links_to_paint[self.n_paths][i]:
                        paths_lk.append(i)
                self.drawLinkToPaint(qp, lk, paths_lk)
            
            for link in self.links_host[self.n_paths]:
                qp.setPen(QPen(Qt.black, 4, Qt.DashLine))
                self.drawLink(qp, link)

            for link in self.links:
                if link not in self.links_painted and link not in self.links_host[self.n_paths]:
                    qp.setPen(QPen(Qt.black, 2))
                    self.drawLink(qp, link)
        else:
            for link in self.links:
                if link not in self.links_painted:
                    qp.setPen(QPen(Qt.black, 2))
                    self.drawLink(qp, link)

        for controller in self.controllers:
            self.drawNodeInfo(qp, controller)

        for switch in self.switches:
            self.drawNodeInfo(qp, switch)

        for host in self.hosts:
            self.drawNodeInfo(qp, host)
                
    def drawLink(self, qp, link):
        fm = QFontMetrics(self.font)
        qp.setFont(self.font)
        start_node = link.start_node
        end_node = link.end_node
        start_pos = start_node.center
        end_pos = end_node.center
        if start_node.name_class not in ("Controller", "Host") and end_node.name_class not in ("Controller", "Host"):
            qp.drawLine(QPoint(*start_pos), QPoint(*end_pos))
            cur_metric = None
            if self.dynamic_metric.metric_show == 'bw':
                cur_metric = str(link.bw) + " Mbps"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'delay':
                cur_metric = str(link.delay) + " ms"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'loss':
                cur_metric = str(link.loss) + "%"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'cost':
                cur_metric = str(link.cost)
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'bw, delay':
                fm_2 = QFontMetrics(QFont('Arial', 12))
                cur_metric = str(link.bw) + " Mbps,\n" + str(link.delay) + " ms"
                cur_metric_1 = str(link.bw) + " Mbps,"
                text_width = fm_2.width(cur_metric_1)
                text_height = fm_2.height()

            mid_point = ((start_pos[0] + end_pos[0]) / 2, (start_pos[1] + end_pos[1]) / 2)
            
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
        elif start_node.name_class == "Host" or end_node.name_class == "Host":
            qp.drawLine(QPoint(*start_pos), QPoint(*end_pos))

    def drawLinkToPaint(self, qp, link, paths_lk):
        distance = 8
        line_width = 3
        fm = QFontMetrics(self.font)
        qp.setFont(self.font)
        start_node = link.start_node
        end_node = link.end_node
        start_pos = start_node.center
        end_pos = end_node.center
        if start_node.name_class!="Controller" and end_node.name_class!="Controller":
            dir_vector = (end_pos[0] - start_pos[0], end_pos[1] - start_pos[1])
            norm = (dir_vector[0]**2 + dir_vector[1]**2)**0.5
            if norm != 0:
                unit_vector = (dir_vector[0]/norm, dir_vector[1]/norm)
                
                perp_vector = (-unit_vector[1], unit_vector[0])
                n = len(paths_lk)
                if n%2 == 0:
                    for i in range(len(paths_lk)):
                        qp.setPen(QPen(self.colors[paths_lk[i]], line_width))
                        if i < n/2:
                            perp_start = (int(start_pos[0] + perp_vector[0] * (distance*(i+0.5))), int(start_pos[1] + perp_vector[1] * (distance*(i+0.5))))
                            perp_end = (int(end_pos[0] + perp_vector[0] * (distance*(i+0.5))), int(end_pos[1] + perp_vector[1] * (distance*(i+0.5))))

                            qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
                        else:
                            perp_start = (int(start_pos[0] - perp_vector[0] * (distance*(i-n/2+0.5))), int(start_pos[1] - perp_vector[1] * (distance*(i-n/2+0.5))))
                            perp_end = (int(end_pos[0] - perp_vector[0] * (distance*(i-n/2+0.5))), int(end_pos[1] - perp_vector[1] * (distance*(i-n/2+0.5))))

                            qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
                else:
                    qp.setPen(QPen(self.colors[paths_lk[0]], line_width))
                    perp_start = (start_pos[0], start_pos[1])
                    perp_end = (end_pos[0], end_pos[1])

                    qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
                    t = int(n/2)
                    for i in range(1, len(paths_lk)):
                        qp.setPen(QPen(self.colors[paths_lk[i]], line_width))
                        if i <= t:
                            perp_start = (int(start_pos[0] + perp_vector[0] * (distance*i + 1)), int(start_pos[1] + perp_vector[1] * (distance*i + 1)))
                            perp_end = (int(end_pos[0] + perp_vector[0] * (distance*i + 1)), int(end_pos[1] + perp_vector[1] * (distance*i + 1)))

                            qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
                        else:
                            perp_start = (int(start_pos[0] - perp_vector[0] * distance*(i-t)), int(start_pos[1] - perp_vector[1] * distance*(i-t)))
                            perp_end = (int(end_pos[0] - perp_vector[0] * distance*(i-t)), int(end_pos[1] - perp_vector[1] * distance*(i-t)))

                            qp.drawLine(QPoint(*perp_start), QPoint(*perp_end))
            cur_metric = None
            if self.dynamic_metric.metric_show == 'bw':
                cur_metric = str(link.bw) + " Mbps"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'delay':
                cur_metric = str(link.delay) + " ms"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'loss':
                cur_metric = str(link.loss) + "%"
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'cost':
                cur_metric = str(link.cost)
                text_width = fm.width(cur_metric)
                text_height = fm.height()
            elif self.dynamic_metric.metric_show == 'bw, delay':
                fm_2 = QFontMetrics(QFont('Arial', 12))
                cur_metric = str(link.bw) + " Mbps,\n" + str(link.delay) + " ms"
                cur_metric_1 = str(link.bw) + " Mbps,"
                text_width = fm_2.width(cur_metric_1)
                text_height = fm_2.height()

            mid_point = ((start_pos[0] + end_pos[0]) / 2, (start_pos[1] + end_pos[1]) / 2)
            
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
        elif start_node.name_class == "Host" or end_node.name_class == "Host":
            qp.drawLine(QPoint(*start_pos), QPoint(*end_pos))

    def drawNodeInfo(self, qp, node):
        node_info = node.name

        fm = QFontMetrics(self.font)
        text_width = fm.width(node_info)
        text_height = fm.height()

        rect_width = text_width 
        rect_height = text_height

        rect_x = node.center[0] - rect_width // 2
        rect_y = node.center[1] - 2*rect_height - 5

        qp.setBrush(Qt.white)
        qp.setPen(Qt.NoPen)
        qp.drawRect(rect_x, rect_y, rect_width, rect_height)

        if node.name_class == "Controller":
            qp.setPen(QColor("blue"))
        elif node.name_class == "Switch":
            qp.setPen(QColor("red"))
        else:
            qp.setPen(QColor("green"))
        qp.setFont(self.font)
        qp.drawText(QRect(rect_x, rect_y, text_width, text_height), Qt.AlignCenter, node_info)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
