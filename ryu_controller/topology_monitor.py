from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.topology import event
from ryu.controller import ofp_event
from ryu.topology.api import get_link, get_switch
import networkx as nx
import logging


class TopologyMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *_args, **_kwargs):
        super(TopologyMonitor, self).__init__(*_args, **_kwargs)
        self.name = "topology_monitor"
        self.datapaths = {}
        self.graph = nx.DiGraph()
        self.logger = logging.getLogger(self.name)

    def _update_topology(self):
        switch_list = get_switch(self, None)
        links = get_link(self, None)
        self._update_graph(switch_list, links)

    def _update_graph(self, switch_list, links):
        new_graph = nx.DiGraph(self.graph)
        for switch in switch_list:
            new_graph.add_node(switch.dp.id)

        for link in links:
            src = link.src
            dst = link.dst

            if self.graph.has_edge(src.dpid, dst.dpid) and self.graph[src.dpid][dst.dpid]['status'] == 'down':
                status = 'down'
            else:
                status = 'up'

            new_graph.add_edge(src.dpid, dst.dpid, weight=1, src_port=src.port_no, dst_port=dst.port_no, status=status)

        self.graph = new_graph


    @set_ev_cls([event.EventSwitchEnter, event.EventSwitchLeave, event.EventLinkAdd, event.EventLinkDelete])
    def _get_topology(self, ev):
        self._update_topology()

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(datapath.id, None)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto

        for u, v, data in list(self.graph.edges(data=True)):
            if (u == dpid and data['src_port'] == port_no) or (v == dpid and data['dst_port'] == port_no):
                if reason == ofproto.OFPPR_DELETE or reason == ofproto.OFPPR_MODIFY:
                    if msg.desc.state & ofproto.OFPPS_LINK_DOWN:
                        self.graph[u][v]['status'] = 'down'
                    elif msg.desc.state & ofproto.OFPPS_BLOCKED:
                        self.graph[u][v]['status'] = 'down'
                    else:
                        self.graph[u][v]['status'] = 'up'
                elif reason == ofproto.OFPPR_ADD:
                    self.graph[u][v]['status'] = 'up'
    
    def get_topology_graph(self):
        return nx.json_graph.node_link_data(self.graph)