from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import arp, tcp, udp
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import ipv6
from ryu.app.wsgi import ControllerBase
import random
import time
from ryu import cfg
from setting import K
from ryu.lib import hub
from ryu.app.wsgi import WSGIApplication, ControllerBase, Response, route
import json

from setting import n_flows, UPDATE_PATHS_PERIOD, time_limit


from YenAlgorithm import YenAlgorithm
from YenAlgorithm_dynamic import YenAlgorithm_dynamic
from delay_monitor import DelayMonitor
from port_monitor import PortMonitor
from topology_monitor import TopologyMonitor

CONF = cfg.CONF

from ABC_dynamic import ABC
from BFA_dynamic import BFA
from FA_dynamic import FA
from AS_dynamic import AS
from ACS_dynamic import ACS
from GA_dynamic import GA

class MultiPathRouting(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
            'wsgi': WSGIApplication,
            'topology_monitor': TopologyMonitor,
            'port_monitor': PortMonitor,
            'delay_monitor': DelayMonitor,
        }

    def __init__(self, *_args, **_kwargs):

        super(MultiPathRouting, self).__init__(*_args, **_kwargs)
        self.name = 'multipath_routing'
        
        wsgi: WSGIApplication = _kwargs['wsgi']
        wsgi.register(NetworkStatRest, {'rest_api_app': self})

        self.topology_monitor: TopologyMonitor = _kwargs['topology_monitor']
        self.port_monitor: PortMonitor = _kwargs['port_monitor']
        self.delay_monitor: DelayMonitor = _kwargs['delay_monitor']
        self.arp_table = {}
        self.hosts = {}
        self.paths_dict = {}
        self.sw = 0
        self.sum_pw = {}
        self.t = 0
        self.routing_background_thread = hub.spawn(self.routing_background)
        self.get_sum_pw_thread = hub.spawn(self.get_sum_pw)


    def routing_background(self):
        while True:
            start_time = time.time()
            keys_list = []
            for key in list(self.paths_dict.keys()):
                if (key[2], key[0]) not in keys_list and (key[0], key[2]) not in keys_list:
                    src_dst = (key[0], key[2])
                    keys_list.append(src_dst)
                    self.update_paths(key)
            end_time = time.time()
            execution_time = end_time - start_time
            sleep_time = max(UPDATE_PATHS_PERIOD - execution_time, 0)
            hub.sleep(sleep_time)
    
    def get_sum_pw(self):
        metric = self.port_monitor.get_link_costs()
        while True:
            hub.sleep(1)
            self.t += 1
            if self.t > 25:
                for key, value in list(self.paths_dict.items()):
                    key_sum = key[-2] + '-->' + key[-1]
                    if key_sum not in self.sum_pw:
                        self.sum_pw[key_sum] = []
                    paths_pw = [self.compute_path_length(metric, path) for path in value[0]]
                    self.sum_pw[key_sum].append(sum(paths_pw))
            if self.t == 45:
                with open('/home/tin/SDN_PyQt5/result/ACS.json', 'w') as f:
                    json.dump(self.sum_pw, f, indent=4)
        
    def compute_path_length(self, metric, path):
        path_length = 0
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            path_length += metric[u][v]
        return float(path_length)
    
    def update_paths(self, key):
        # alg = YenAlgorithm_dynamic(self.port_monitor, self.paths_dict, key, K)
        # alg = GA(self.port_monitor, self.paths_dict, key, K, 10, 100000, 0.7, 0.7, 2)
        # alg = ABC(self.port_monitor, self.paths_dict, key, K, 10, 100000, 20)
        # alg = BFA(self.port_monitor, self.paths_dict, key, K, 10, 100000, 0.7, 2, 2)
        # alg = AS(self.port_monitor, self.paths_dict, key, K, 10, 100000, 0.1, 1, 1, 0.5, 1)
        alg = ACS(self.port_monitor, self.paths_dict, key, K, 10, 100000, 0.1, 1, 1, 0.5, 1)
        # alg = FA(self.port_monitor, self.paths_dict, key, K, 10, 100000, 1, 1, 1, True)
        
        alg.compute_shortest_paths(time_limit)

    def get_optimal_paths(self, src, dst):
        metric = self.port_monitor.get_link_costs()
        alg = YenAlgorithm(metric, src, dst, K)
        paths, paths_edges, pw = alg.compute_shortest_paths()
        return paths, paths_edges, pw
    
    def make_normalized(self, pw):
        pw = [100 if item == 0 else 1/item for item in pw]
        total = sum(pw)
        normalized_pw = [round(float(i)/total, 2) for i in pw]
        normalized_pw[-1] += 1 - sum(normalized_pw)
        normalized_pw[-1] = round(normalized_pw[-1], 2)
        return normalized_pw

    def add_ports_to_paths(self, paths, first_port, last_port):
        paths_p = []
        for path in paths:
            p = {}
            in_port = first_port
            for s1, s2 in zip(path[:-1], path[1:]):
                out_port = self.topology_monitor.graph[s1][s2]['src_port']
                p[s1] = (in_port, out_port)
                in_port = self.topology_monitor.graph[s1][s2]['dst_port']
            p[path[-1]] = (in_port, last_port)
            paths_p.append(p)
        return paths_p

    def install_paths_arp(self, src, first_port, dst, last_port, ip_src, ip_dst, paths, pw):
        paths_with_ports = self.add_ports_to_paths(paths, first_port, last_port)
        selected_path = random.choices(paths_with_ports, weights=pw, k=1)[0]
        for node in selected_path:

            dp = self.topology_monitor.datapaths[node]
            ofp = dp.ofproto
            ofp_parser = dp.ofproto_parser
            actions = []
            in_port = selected_path[node][0]
            out_port = selected_path[node][1]

            match_ip = ofp_parser.OFPMatch(
                in_port=in_port,
                ip_proto=1,
                eth_type=0x0800, 
                ipv4_src=ip_src, 
                ipv4_dst=ip_dst
            )
            match_arp = ofp_parser.OFPMatch(
                in_port=in_port,
                eth_type=0x0806, 
                arp_spa=ip_src, 
                arp_tpa=ip_dst
            )
               
            actions = [ofp_parser.OFPActionOutput(out_port)]
            self.add_flow(dp, 32768, match_ip, actions)
            self.add_flow(dp, 1, match_arp, actions)

        return selected_path[src][1]
    
    def install_paths_ip(self, src, first_port, dst, last_port, ip_src, ip_dst, paths, pw, index, tcp_pkt, udp_pkt):
        paths_with_ports = self.add_ports_to_paths(paths, first_port, last_port)
        selected_path = paths_with_ports[index]
        for node in selected_path:

            dp = self.topology_monitor.datapaths[node]
            ofp = dp.ofproto
            ofp_parser = dp.ofproto_parser
            actions = []
            in_port = selected_path[node][0]
            out_port = selected_path[node][1]

            match_ip = None
            if tcp_pkt:
                match_ip = ofp_parser.OFPMatch(
                        in_port=in_port,
                        ip_proto=6,
                        eth_type=0x0800,
                        ipv4_src=ip_src, 
                        ipv4_dst=ip_dst,
                        tcp_src=tcp_pkt.src_port,
                        tcp_dst=tcp_pkt.dst_port
                    )
            elif udp_pkt:
                match_ip = ofp_parser.OFPMatch(
                        in_port=in_port,
                        ip_proto=17,
                        eth_type=0x0800,
                        ipv4_src=ip_src, 
                        ipv4_dst=ip_dst,
                        udp_src=udp_pkt.src_port,
                        udp_dst=udp_pkt.dst_port
                    ) 
            actions = [ofp_parser.OFPActionOutput(out_port)]    
            self.add_flow(dp, 32768, match_ip, actions)

        return selected_path[src][1]

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        self.sw = self.sw +1
        print ("switch_features_handler "+str(self.sw) + " is called")
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)
        udp_pkt = pkt.get_protocol(udp.udp)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        if eth.ethertype == 35020:
            return

        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return None

        src = eth.src
        dst = eth.dst

        dpid = datapath.id

        if src not in self.hosts:
            self.hosts[src] = (dpid, in_port)

        out_port = ofproto.OFPP_FLOOD

        if arp_pkt:
            src_ip = arp_pkt.src_ip
            dst_ip = arp_pkt.dst_ip
            if arp_pkt.opcode == arp.ARP_REQUEST:
                if dst_ip in self.arp_table:
                    self.arp_table[src_ip] = src
                    dst_mac = self.arp_table[dst_ip]
                    h1 = self.hosts[src]
                    h2 = self.hosts[dst_mac]
                    paths, paths_edges, pw = self.get_optimal_paths(h1[0], h2[0])
                    normalize_pw = self.make_normalized(pw)
                    out_port = self.install_paths_arp(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw)

                    paths_reverse, paths_edges_reverse, pw_reverse = self.get_optimal_paths(h2[0], h1[0])
                    normalize_pw_reverse = self.make_normalized(pw_reverse)
                    self.install_paths_arp(h2[0], h2[1], h1[0], h1[1], dst_ip, src_ip, paths_reverse, normalize_pw_reverse)

            elif arp_pkt.opcode == arp.ARP_REPLY:
                self.arp_table[src_ip] = src
                h1 = self.hosts[src]
                h2 = self.hosts[dst]
                paths, paths_edges, pw = self.get_optimal_paths(h1[0], h2[0])
                normalize_pw = self.make_normalized(pw)
                out_port = self.install_paths_arp(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw)

                paths_reverse, paths_edges_reverse, pw_reverse = self.get_optimal_paths(h2[0], h1[0])
                normalize_pw_reverse = self.make_normalized(pw_reverse)
                self.install_paths_arp(h2[0], h2[1], h1[0], h1[1], dst_ip, src_ip, paths_reverse, normalize_pw_reverse)

            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(
                datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                actions=actions, data=data)
            datapath.send_msg(out)

        if tcp_pkt or udp_pkt:
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            h1 = self.hosts[src]
            h2 = self.hosts[dst]
                
            paths, paths_edges, pw = [], [], []
            if (h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip) not in list(self.paths_dict.keys()):
                paths, paths_edges, pw = self.get_optimal_paths(h1[0], h2[0])
                src_dst = "Round Robin: " + src_ip + " --> " + dst_ip
                self.paths_dict[(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip)] = [paths, paths_edges, pw, src_ip, dst_ip, 0, src_dst]
                normalize_pw = self.make_normalized(pw)
                out_port = self.install_paths_ip(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw, 0, tcp_pkt, udp_pkt)

                actions = [parser.OFPActionOutput(out_port)]
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                    actions=actions, data=data)
                datapath.send_msg(out)

            else:
                [paths, paths_edges, pw, x1, x2, index, x3] = self.paths_dict[(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip)]
                next_index = (index+1)%len(paths)
                normalize_pw = self.make_normalized(pw)
                out_port = self.install_paths_ip(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw, next_index, tcp_pkt, udp_pkt)
                self.paths_dict[(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip)][5] = next_index

                actions = [parser.OFPActionOutput(out_port)]
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                    actions=actions, data=data)
                datapath.send_msg(out)
    
class NetworkStatRest(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(NetworkStatRest, self).__init__(req, link, data, **config)
        self.app: MultiPathRouting = data['rest_api_app']

    @route('rest_api_app', '/', methods=['GET'])
    def hello(self, req, **_kwargs):
        body = json.dumps([{'hello': 'world'}])
        return (Response(content_type='application/json', body=body, status=200))
    
    @route('rest_api_app', '/topology_graph', methods=['GET'])
    def get_topology_graph(self, req, **kwargs):
        graph = self.app.topology_monitor.get_topology_graph()
        body = json.dumps(graph)
        return Response(content_type='application/json', body=body, status=200)

    @route('rest_api_app', '/latency', methods=['GET'])
    def get_latency(self, req, **kwargs):
        latency = self.app.delay_monitor.get_latency()
        body = json.dumps(latency)
        return Response(content_type='application/json', body=body, status=200)
    
    @route('rest_api_app', '/throughput', methods=['GET'])
    def get_throughput(self, req, **kwargs):
        throughput = self.app.port_monitor.get_throughput()
        body = json.dumps(throughput)
        return Response(content_type='application/json', body=body, status=200)
    
    @route('rest_api_app', '/rm_bw', methods=['GET'])
    def get_rm_bw(self, req, **kwargs):
        rm_bw = self.app.port_monitor.get_rm_bw()
        body = json.dumps(rm_bw)
        return Response(content_type='application/json', body=body, status=200)
    
    @route('rest_api_app', '/paths', methods=['GET'])
    def get_paths(self, req, **kwargs):
        paths_dict = {}
        if len(self.app.paths_dict) != 0:
            i = 0
            for key, item in self.app.paths_dict.items():
                paths_dict[i] = item
                i += 1
        body = json.dumps(paths_dict)
        return Response(content_type='application/json', body=body, status=200)