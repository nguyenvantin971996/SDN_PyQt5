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
import copy
import itertools
import time
from ryu import cfg
from setting import K, patience, MAX_CAPACITY
from ryu.lib import hub
from ryu.app.wsgi import WSGIApplication, ControllerBase, Response, route
import json
from decimal import Decimal

from setting import n_flows, UPDATE_PATHS_PERIOD, time_limit

from delay_monitor import DelayMonitor
from port_monitor import PortMonitor
from topology_monitor import TopologyMonitor
from flow_monitor import FlowMonitor

CONF = cfg.CONF

from YenAlgorithm import YenAlgorithm
from YenAlgorithm_dynamic import YenAlgorithm_dynamic
from ABC_static import ABC
from BFA_static import BFA
from FA_static import FA
from AS_static import AS
from ACS_static import ACS
from GA_static import GA

class MultiPathRouting(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
            'wsgi': WSGIApplication,
            'topology_monitor': TopologyMonitor,
            'port_monitor': PortMonitor,
            'delay_monitor': DelayMonitor,
            'flow_monitor': FlowMonitor
        }

    def __init__(self, *_args, **_kwargs):

        super(MultiPathRouting, self).__init__(*_args, **_kwargs)
        self.name = 'multipath_routing'
        
        wsgi: WSGIApplication = _kwargs['wsgi']
        wsgi.register(NetworkStatRest, {'rest_api_app': self})

        self.topology_monitor: TopologyMonitor = _kwargs['topology_monitor']
        self.port_monitor: PortMonitor = _kwargs['port_monitor']
        self.delay_monitor: DelayMonitor = _kwargs['delay_monitor']
        self.flow_monitor: FlowMonitor = _kwargs['flow_monitor']
        self.arp_table = {}
        self.hosts = {}
        self.paths_dict = {}
        self.si_instances = {}
        self.sw = 0
        self.sum_pw = {}
        self.t = 0
        # self.routing_background_thread = hub.spawn(self.routing_background)

    def routing_background(self):
        while True:
            self.rerouting()
            self.update_pw()
            hub.sleep(UPDATE_PATHS_PERIOD)

    def get_overloaded_links(self):
        overloaded_links = []
        metric = self.port_monitor.get_link_costs()
        for src in metric:
            for dst in metric[src]:
                link_cost = metric[src][dst]
                if link_cost is not None and link_cost >= Decimal('100'):
                    overloaded_links.append((src, dst))
        return overloaded_links
    
    def compute_pw(self, metric, paths_edges):
        pw = []
        for path_edges in paths_edges:
            length = 0
            for edge in path_edges:
                u = edge[0]
                v = edge[1]
                length += metric[u][v]
            pw.append(float(length))
        return pw
    
    def update_pw(self):
        metric = self.port_monitor.get_link_costs()
        tmp_paths_dict = copy.deepcopy(self.paths_dict)
        for key, path_info in tmp_paths_dict.items():
            paths, paths_edges, pw, x1, x2, x3, x4 = copy.deepcopy(path_info)
            pw = copy.deepcopy(self.compute_pw(metric, paths_edges))
            self.paths_dict[key][2] = pw

    def rerouting(self):
        overloaded_links = self.get_overloaded_links()
        if len(overloaded_links)!=0:
            all_flows_overloaded = self.get_flows_overloaded(overloaded_links)
            link_costs = self.get_costs_to_adapt(overloaded_links, all_flows_overloaded)
            metric = self.port_monitor.get_link_costs()
            tmp_paths_dict = copy.deepcopy(self.paths_dict)
            for key, path_info in tmp_paths_dict.items():
                old_paths, old_paths_edges, old_pw, src_ip, dst_ip, src_dst, streams = copy.deepcopy(path_info)
                streams_overloaded = []
                paths_rerouting_index = []
                for path_index, tcp_pkt, udp_pkt in streams:
                    flow = None
                    if tcp_pkt:
                        flow = (6, src_ip, dst_ip, tcp_pkt.src_port, None)
                    if udp_pkt:
                        flow = (17, src_ip, dst_ip, None, udp_pkt.src_port)
                    if flow in all_flows_overloaded:
                        streams_overloaded.append((path_index, tcp_pkt, udp_pkt))
                        if path_index not in paths_rerouting_index:
                            paths_rerouting_index.append(path_index)
                src = key[0]
                first_port = key[1]
                dst = key[2]
                last_port = key[3]
                new_k = len(paths_rerouting_index)
                alg = YenAlgorithm(link_costs, src, dst, new_k)
                # alg = ABC(link_costs, src, dst, new_k, 10, 100, 20)
                new_paths, new_paths_edges, new_pw = alg.compute_shortest_paths()
                paths, paths_edges, pw, x1, x2, x3, x4 = copy.deepcopy(path_info)
                for idx in range(len(paths_rerouting_index)):
                    x = paths_rerouting_index[idx]
                    paths[x] = copy.deepcopy(new_paths[idx])
                    paths_edges[x] = copy.deepcopy(new_paths_edges[idx])
                pw = copy.deepcopy(self.compute_pw(metric, paths_edges))
                self.paths_dict[key][0] = paths
                self.paths_dict[key][1] = paths_edges
                self.paths_dict[key][2] = pw
                normalize_pw = self.make_normalized(pw)
                old_normalize_pw = self.make_normalized(old_pw)
                for path_index, tcp_pkt, udp_pkt in streams_overloaded:
                    self.delete_paths_ip(src, first_port, dst, last_port, src_ip, dst_ip,
                                        old_paths, old_normalize_pw, path_index, tcp_pkt, udp_pkt)
                    self.install_paths_ip(src, first_port, dst, last_port, src_ip, dst_ip,
                                        paths, normalize_pw, path_index, tcp_pkt, udp_pkt)
                   
    def get_flows_overloaded(self, overloaded_links):
        capacity = MAX_CAPACITY
        all_overload_flows = set()
        for src, dst in overloaded_links:
            if src in self.flow_monitor.switch_to_switch_flows_speed:
                if dst in self.flow_monitor.switch_to_switch_flows_speed[src]:
                    flows = {}
                    for key_flow, speed in self.flow_monitor.switch_to_switch_flows_speed[src][dst].items():
                        if key_flow[0] == 17:
                            flows[key_flow] = speed
                    chosen_flow_set = self.find_valid_flow_sets(flows, capacity)
                    if chosen_flow_set:
                        flow_set, total_speed = chosen_flow_set
                        flow_set_as_set = set(flow_set)
                        all_overload_flows.update(flow_set_as_set)
        return all_overload_flows

    def find_valid_flow_sets(self, flows, capacity):
        flow_keys = list(flows.keys())
        valid_sets = []  
        for r in range(len(flow_keys) + 1):
            for subset in itertools.combinations(flow_keys, r):
                remaining_keys = set(flow_keys) - set(subset)
                total_remaining_speed = sum(flows[key] for key in remaining_keys)
                link_utilization = round(total_remaining_speed / capacity, 1)       
                if link_utilization < 1:
                    valid_subset = True
                    for flow in subset:
                        new_utilization = round((total_remaining_speed + flows[flow]) / capacity, 1)
                        if new_utilization < 1:
                            valid_subset = False
                            break
                    if valid_subset:
                        sorted_subset = sorted(subset, key=lambda k: flows[k], reverse=True)
                        total_speed = sum(flows[key] for key in subset)
                        valid_sets.append((sorted_subset, total_speed))
        if not valid_sets:
            return None
        min_size = min(len(flow_set) for flow_set, _ in valid_sets)
        smallest_flow_sets = [(flow_set, total_speed) for flow_set, total_speed in valid_sets if len(flow_set) == min_size]
        max_speed = max(total_speed for _, total_speed in smallest_flow_sets)
        overload_flow_set = [(flow_set, total_speed) for flow_set, total_speed in smallest_flow_sets if total_speed == max_speed][0]
        
        return overload_flow_set

    def get_costs_to_adapt(self, overloaded_links, flows_overloaded):
        capacity = MAX_CAPACITY
        link_costs = copy.deepcopy(self.port_monitor.get_link_costs())
        thr = self.port_monitor.get_throughput()
        for src in self.flow_monitor.switch_to_switch_flows_speed:
            for dst in self.flow_monitor.switch_to_switch_flows_speed[src]:
                dk = False
                s = thr[src][dst] if (src, dst) not in overloaded_links else 0
                for flow_key, flow_speed in self.flow_monitor.switch_to_switch_flows_speed[src][dst].items():
                    if (src, dst) in overloaded_links:
                        if flow_key not in flows_overloaded:
                            s += flow_speed
                            dk = True
                    else:
                        if flow_key in flows_overloaded:
                            s =  max(0, s-flow_speed)
                            dk = True
                if dk:
                    link_utilization = round(s/capacity, 1)
                    if link_utilization >= 1:
                        link_costs[src][dst] = Decimal('100')
                    else:
                        link_costs[src][dst] = Decimal(str(round(1 / (1 - link_utilization), 1)))
        return link_costs

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

    def install_paths_arp(self, src, first_port, dst, last_port, ip_src, ip_dst, paths):
        paths_with_ports = self.add_ports_to_paths(paths, first_port, last_port)
        selected_path = paths_with_ports[0]
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
            self.add_flow(dp, 1, match_ip, actions)
            self.add_flow(dp, 1, match_arp, actions)
        return selected_path[src][1]
    
        
    def delete_paths_ip(self, src, first_port, dst, last_port, ip_src, ip_dst, paths, pw, index, tcp_pkt, udp_pkt):
        paths_with_ports = self.add_ports_to_paths(paths, first_port, last_port)
        selected_path = paths_with_ports[index]
        for node in selected_path:
            dp = self.topology_monitor.datapaths[node]
            ofp_parser = dp.ofproto_parser
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
            self.remove_flows(dp, match_ip, out_port)
        return
    
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

    def remove_flows(self, datapath, match, out_port):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE,
                                out_port=out_port, match=match)
        datapath.send_msg(mod)
    
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
                    paths, _, _ = self.get_optimal_paths(h1[0], h2[0])
                    out_port = self.install_paths_arp(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths)

                    paths_reverse, _, _ = self.get_optimal_paths(h2[0], h1[0])
                    self.install_paths_arp(h2[0], h2[1], h1[0], h1[1], dst_ip, src_ip, paths_reverse)

            elif arp_pkt.opcode == arp.ARP_REPLY:
                self.arp_table[src_ip] = src
                h1 = self.hosts[src]
                h2 = self.hosts[dst]
                paths, _, _ = self.get_optimal_paths(h1[0], h2[0])
                out_port = self.install_paths_arp(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths)

                paths_reverse, _, _ = self.get_optimal_paths(h2[0], h1[0])
                self.install_paths_arp(h2[0], h2[1], h1[0], h1[1], dst_ip, src_ip, paths_reverse)

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
            proto_type = 'tcp' if tcp_pkt else 'udp'       
            if (h1[0], h1[1], h2[0], h2[1], proto_type) not in list(self.paths_dict.keys()):
                paths, paths_edges, pw = self.get_optimal_paths(h1[0], h2[0])
                src_dst = f"Round Robin: {proto_type.upper()} {src_ip} --> {dst_ip}"
                streams = []
                streams.append((0, tcp_pkt, udp_pkt))
                
                self.paths_dict[(h1[0], h1[1], h2[0], h2[1], proto_type)] = [paths, paths_edges, pw, src_ip, dst_ip, src_dst, streams]
                
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
                [paths, paths_edges, pw, x1, x2, x3, streams] = self.paths_dict[(h1[0], h1[1], h2[0], h2[1], proto_type)]
                index = streams[-1][0]
                next_index = (index + 1) % len(paths)

                normalize_pw = self.make_normalized(pw)
                out_port = self.install_paths_ip(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw, next_index, tcp_pkt, udp_pkt)
                
                self.paths_dict[(h1[0], h1[1], h2[0], h2[1], proto_type)][-1].append((next_index, tcp_pkt, udp_pkt))

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
        rm_bw = self.app.port_monitor.get_remaining_bandwidth()
        body = json.dumps(rm_bw)
        return Response(content_type='application/json', body=body, status=200)
    
    @route('rest_api_app', '/paths', methods=['GET'])
    def get_paths(self, req, **kwargs):
        paths_dict = {}
        if len(self.app.paths_dict) != 0:
            i = 0
            for key, item in self.app.paths_dict.items():
                if 'udp' in key:
                    itm = item[:6]
                    paths_dict[i] = itm
                    i += 1
        body = json.dumps(paths_dict)
        return Response(content_type='application/json', body=body, status=200)