from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.topology import event
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.topology.api import get_link, get_switch, get_host

from setting import DISCOVERY_PERIOD
from ryu.lib import hub
import networkx as nx

class TopologyMonitor(app_manager.RyuApp):
    
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    def __init__(self, *_args, **_kwargs):
        super(TopologyMonitor, self).__init__(*_args, **_kwargs)
        self.name = "topology_monitor"
        self.topology_api_app = self
        self.discover_thread = hub.spawn(self._discover_thread)
        self.datapaths = {}
        self.switches = []
        self.switch_port_table = {}
        self.access_ports = {}
        self.interior_ports = {}
        self.link_to_port = {}
        self.graph = nx.DiGraph()
        
    def _discover_thread(self):
        while True:
            hub.sleep(DISCOVERY_PERIOD)
    
    def _get_graph(self, link_list):
        for src in self.switches:
            for dst in self.switches:
                if src == dst:
                    self.graph.add_edge(src, dst, weight=0)
                    self.graph[src][dst]['port'] = (None, None)
                elif (src, dst) in link_list.keys():
                    self.graph.add_edge(src, dst, weight=1)
                    self.graph[src][dst]['port'] = link_list[(src, dst)]
        return self.graph
    
    def _create_port_map(self, switch_list):
        for sw in switch_list:
            dpid = sw.dp.id
            self.switch_port_table.setdefault(dpid, set())
            self.interior_ports.setdefault(dpid, set())
            self.access_ports.setdefault(dpid, set())
            for p in sw.ports:
                self.switch_port_table[dpid].add(p.port_no)

    def _create_access_ports(self):
        for sw in self.switch_port_table:
            all_port_table = self.switch_port_table[sw]
            interior_port = self.interior_ports[sw]
            self.access_ports[sw] = all_port_table - interior_port

    def _create_interior_links(self, link_list):
        for link in link_list:
            src = link.src
            dst = link.dst
            self.link_to_port[(src.dpid, dst.dpid)] = (src.port_no, dst.port_no)

            if link.src.dpid in self.switches:
                self.interior_ports[link.src.dpid].add(link.src.port_no)
            if link.dst.dpid in self.switches:
                self.interior_ports[link.dst.dpid].add(link.dst.port_no)
    
    @set_ev_cls([event.EventSwitchEnter,
                 event.EventSwitchLeave, event.EventPortAdd,
                 event.EventPortDelete, event.EventPortModify,
                 event.EventLinkAdd, event.EventLinkDelete])        
    def _get_topology(self, ev):
        switch_list = get_switch(self.topology_api_app, None)
        self._create_port_map(switch_list)
        self.switches = list(self.switch_port_table.keys())
        links = get_link(self.topology_api_app, None)
        self._create_interior_links(links)
        self._create_access_ports()
        self._get_graph(self.link_to_port)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]
        
    def get_link_to_port(self, src_dpid, dst_dpid):
        if (src_dpid, dst_dpid) in self.link_to_port:
            return self.link_to_port[(src_dpid, dst_dpid)]
        else:
            self.logger.info("dpid:%s->dpid:%s is not in links" % (src_dpid, dst_dpid))
            return None

    def get_topology_data(self):
        hosts = get_host(self, None)
        switches = get_switch(self, None)
        links = get_link(self, None)

        hosts_dict = [host.to_dict() for host in hosts]
        switches_dict = [switch.to_dict() for switch in switches]
        links_dict = [link.to_dict() for link in links]
        return hosts_dict, switches_dict, links_dict

    
    def get_hosts(self):
        hosts = get_host(self, None)
        return [host.to_dict() for host in hosts]
    
    def get_switches(self):
        switches = get_switch(self)
        return [switch.to_dict() for switch in switches]
        
    
    def get_links(self):
        links = get_link(self)
        return [link.to_dict() for link in links]

    def get_topology_graph(self):
        return nx.json_graph.node_link_data(self.graph)