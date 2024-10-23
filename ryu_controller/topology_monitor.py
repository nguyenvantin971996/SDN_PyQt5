# Импорт библиотек для работы с Ryu и графами сети
from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.topology import event
from ryu.controller import ofp_event
from ryu.topology.api import get_link, get_switch
import networkx as nx
import logging

# Класс приложения для мониторинга топологии сети
class TopologyMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):
        # Инициализация атрибутов для хранения информации о сети
        super(TopologyMonitor, self).__init__(*_args, **_kwargs)
        self.name = "topology_monitor"  # Название приложения
        self.datapaths = {}  # Словарь для хранения datapath коммутаторов
        self.graph = nx.DiGraph()  # Граф для хранения топологии сети

    # Обновление топологии сети с использованием API Ryu
    def _update_topology(self):
        switch_list = get_switch(self, None)
        links = get_link(self, None)
        self._update_graph(switch_list, links)

    # Обновление графа сети с учетом состояния каналов и коммутаторов
    def _update_graph(self, switch_list, links):
        new_graph = nx.DiGraph(self.graph)

        # Добавление всех коммутаторов в граф
        for switch in switch_list:
            new_graph.add_node(switch.dp.id)

        # Добавление всех каналов между коммутаторами
        for link in links:
            src = link.src
            dst = link.dst

            # Проверка статуса канала
            if self.graph.has_edge(src.dpid, dst.dpid) and self.graph[src.dpid][dst.dpid]['status'] == 'down':
                status = 'down'
            else:
                status = 'up'

            # Добавление ребра в граф с атрибутами канала
            new_graph.add_edge(src.dpid, dst.dpid, weight=1, src_port=src.port_no, dst_port=dst.port_no, status=status)

        # Обновление графа сети
        self.graph = new_graph

    # Обработка событий изменения топологии (добавление/удаление коммутаторов и каналов)
    @set_ev_cls([event.EventSwitchEnter, event.EventSwitchLeave, event.EventLinkAdd, event.EventLinkDelete])
    def _get_topology(self, ev):
        self._update_topology()

    # Обработка событий изменения состояния коммутаторов
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath  # Добавление коммутатора в список datapath
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(datapath.id, None)  # Удаление коммутатора из списка при отключении

    # Обработчик событий изменения состояния портов (доступность/недоступность портов)
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto

        # Обновление статуса канала на основе изменений портов
        for u, v, data in list(self.graph.edges(data=True)):
            if (u == dpid and data['src_port'] == port_no) or (v == dpid and data['dst_port'] == port_no):
                # Обработка события удаления или изменения порта
                if reason == ofproto.OFPPR_DELETE or reason == ofproto.OFPPR_MODIFY:
                    if msg.desc.state & ofproto.OFPPS_LINK_DOWN:
                        self.graph[u][v]['status'] = 'down'
                    elif msg.desc.state & ofproto.OFPPS_BLOCKED:
                        self.graph[u][v]['status'] = 'down'
                    else:
                        self.graph[u][v]['status'] = 'up'
                # Обработка события добавления порта
                elif reason == ofproto.OFPPR_ADD:
                    self.graph[u][v]['status'] = 'up'
    
    # Получение графа топологии сети в формате JSON
    def get_topology_graph(self):
        return nx.json_graph.node_link_data(self.graph)