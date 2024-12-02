from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, arp, tcp, udp, ethernet, ipv4, ipv6, icmp
from ryu.app.wsgi import WSGIApplication, ControllerBase, Response, route

import json
import copy
from setting import K, MAX_VALUE

from delay_monitor import DelayMonitor
from port_monitor import PortMonitor
from topology_monitor import TopologyMonitor
from flow_monitor import FlowMonitor

from Yen import Yen

class MultiPathLoadBalancing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {
            'wsgi': WSGIApplication,
            'topology_monitor': TopologyMonitor,
            'port_monitor': PortMonitor,
            'delay_monitor': DelayMonitor,
            'flow_monitor': FlowMonitor
        }

    def __init__(self, *_args, **_kwargs):

        super(MultiPathLoadBalancing, self).__init__(*_args, **_kwargs)
        self.name = 'multipath_load_balancing'
        
        wsgi: WSGIApplication = _kwargs['wsgi']
        wsgi.register(NetworkStatRest, {'rest_api_app': self})

        # Мониторинг топологии, портов, задержек и потоков
        self.topology_monitor: TopologyMonitor = _kwargs['topology_monitor']
        self.port_monitor: PortMonitor = _kwargs['port_monitor']
        self.delay_monitor: DelayMonitor = _kwargs['delay_monitor']
        self.flow_monitor: FlowMonitor = _kwargs['flow_monitor']

        # Инициализация таблиц и переменных
        self.ip_to_mac_map = {}
        self.hosts_map = {}
        self.paths_cache = {}
        self.switch_count = 0

    # Обработка события при подключении нового коммутатора
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        self.switch_count = self.switch_count +1
        print ("switch_features_handler "+str(self.switch_count) + " is called")
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.install_flow(datapath, 0, match, actions)

    # Обработка события прихода пакета на контроллер
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)
        udp_pkt = pkt.get_protocol(udp.udp)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        icmp_pkt = pkt.get_protocol(icmp.icmp)

        if eth.ethertype == 35020:
            return

        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.install_flow(datapath, 1, match, actions)
            return None

        mac_src = eth.src
        dpid = datapath.id

        if mac_src not in self.hosts_map:
            self.hosts_map[mac_src] = (dpid, in_port)

        # Обработка ARP
        if arp_pkt:
            self.handle_arp(datapath, in_port, pkt, arp_pkt, msg)
            return
        
        # Обработка ICMP
        if icmp_pkt:
            self.handle_icmp(datapath, in_port, pkt, ip_pkt, icmp_pkt, msg)
            return

        # Обработка TCP и UDP
        if tcp_pkt or udp_pkt:
            self.handle_tcp_udp(datapath, in_port, pkt, ip_pkt, tcp_pkt, udp_pkt, msg)
            return
            
    def handle_arp(self, datapath, in_port, pkt, arp_pkt, msg):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        eth = pkt.get_protocol(ethernet.ethernet)
        src_ip = arp_pkt.src_ip
        dst_ip = arp_pkt.dst_ip
        mac_src = eth.src
        mac_dst = eth.dst

        self.ip_to_mac_map[src_ip] = mac_src  # Обновляем карту IP-MAC

        if arp_pkt.opcode == arp.ARP_REQUEST:
            if dst_ip in self.ip_to_mac_map:
                dst_mac = self.ip_to_mac_map[dst_ip]
                # Формируем ARP Reply
                arp_reply = packet.Packet()
                arp_reply.add_protocol(
                    ethernet.ethernet(
                        ethertype=eth.ethertype,
                        src=dst_mac,
                        dst=mac_src
                    )
                )
                arp_reply.add_protocol(
                    arp.arp(
                        opcode=arp.ARP_REPLY,
                        src_mac=dst_mac,
                        src_ip=dst_ip,
                        dst_mac=mac_src,
                        dst_ip=src_ip
                    )
                )
                arp_reply.serialize()
                actions = [parser.OFPActionOutput(in_port)]
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
                    in_port=ofproto.OFPP_CONTROLLER,
                    actions=actions, data=arp_reply.data
                )
                datapath.send_msg(out)
            else:
                actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id,
                    in_port=in_port, actions=actions, data=msg.data
                )
                datapath.send_msg(out)

        elif arp_pkt.opcode == arp.ARP_REPLY:
            if mac_dst in self.hosts_map:
                out_port = self.hosts_map[mac_dst][1]
                actions = [parser.OFPActionOutput(out_port)]
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id,
                    in_port=in_port, actions=actions, data=msg.data
                )
                datapath.send_msg(out)

    def handle_icmp(self, datapath, in_port, pkt, ip_pkt, icmp_pkt, msg):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        eth = pkt.get_protocol(ethernet.ethernet)
        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        mac_src = eth.src
        mac_dst = eth.dst

        if icmp_pkt.type == icmp.ICMP_ECHO_REQUEST:
            icmp_reply = packet.Packet()
            icmp_reply.add_protocol(
                ethernet.ethernet(
                    ethertype=eth.ethertype,
                    src=mac_dst,
                    dst=mac_src
                )
            )
            icmp_reply.add_protocol(
                ipv4.ipv4(
                    dst=src_ip,
                    src=dst_ip,
                    proto=ip_pkt.proto
                )
            )
            icmp_reply.add_protocol(
                icmp.icmp(
                    type_=icmp.ICMP_ECHO_REPLY,
                    code=icmp.ICMP_ECHO_REPLY_CODE,
                    csum=0,
                    data=icmp_pkt.data
                )
            )
            icmp_reply.serialize()
            actions = [parser.OFPActionOutput(in_port)]
            out = parser.OFPPacketOut(
                datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=ofproto.OFPP_CONTROLLER,
                actions=actions, data=icmp_reply.data
            )
            datapath.send_msg(out)
        else:
            if mac_dst in self.hosts_map:
                out_port = self.hosts_map[mac_dst][1]
                actions = [parser.OFPActionOutput(out_port)]
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id,
                    in_port=in_port, actions=actions, data=msg.data
                )
                datapath.send_msg(out)
    
    def handle_tcp_udp(self, datapath, in_port, pkt, ip_pkt, tcp_pkt, udp_pkt, msg):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        eth = pkt.get_protocol(ethernet.ethernet)
        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        mac_src = eth.src
        mac_dst = eth.dst
        src_sw_in_port = self.hosts_map[mac_src]
        dst_sw_in_port = self.hosts_map[mac_dst]
        
        proto_type = 'tcp' if tcp_pkt else 'udp'
        key = (src_sw_in_port[0], src_sw_in_port[1], dst_sw_in_port[0], dst_sw_in_port[1], proto_type)

        if key not in list(self.paths_cache.keys()):
            paths_nodes, paths_edges, paths_weights = self.calculate_best_paths(src_sw_in_port[0], dst_sw_in_port[0])
            src_dst = f"ECMP: {proto_type.upper()} {src_ip} --> {dst_ip}"
            streams = []
            initial_index = 0
            streams.append((initial_index, tcp_pkt, udp_pkt))
            self.paths_cache[key] = [paths_nodes, paths_edges, paths_weights, src_ip, dst_ip, src_dst, streams]
            out_port = self.set_paths_tcp_udp(src_sw_in_port[0], src_sw_in_port[1], dst_sw_in_port[0], dst_sw_in_port[1], src_ip, dst_ip, paths_nodes, initial_index, tcp_pkt, udp_pkt)

            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(
                datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                actions=actions, data=data)
            datapath.send_msg(out)

        else:
            [paths_nodes, paths_edges, paths_weights, x1, x2, x3, streams] = self.paths_cache[key]
            index = streams[-1][0]
            next_index = (index + 1) % len(paths_nodes)
            self.paths_cache[key][-1].append((next_index, tcp_pkt, udp_pkt))
            out_port = self.set_paths_tcp_udp(src_sw_in_port[0], src_sw_in_port[1], dst_sw_in_port[0], dst_sw_in_port[1], src_ip, dst_ip, paths_nodes, next_index, tcp_pkt, udp_pkt)
            
            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(
                datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                actions=actions, data=data)
            datapath.send_msg(out) 
    
    # Установка потоков по IP для TCP и UDP
    def set_paths_tcp_udp(self, src, in_port_src_sw, dst, out_port_dst_sw, ip_src, ip_dst, paths_nodes, index, tcp_pkt, udp_pkt):
        paths_with_ports = self.paths_ports(paths_nodes, in_port_src_sw, out_port_dst_sw)
        selected_path = paths_with_ports[index]
        for node in selected_path:
            dp = self.topology_monitor.datapaths[node]
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
            self.install_flow(dp, 32768, match_ip, actions)
        return selected_path[src][1]

    # Добавление портов к путям
    def paths_ports(self, paths_nodes, in_port_src_sw, out_port_dst_sw):
        paths_p = []
        for path in paths_nodes:
            p = {}
            in_port = in_port_src_sw
            for s1, s2 in zip(path[:-1], path[1:]):
                out_port = self.topology_monitor.graph[s1][s2]['src_port']
                p[s1] = (in_port, out_port)
                in_port = self.topology_monitor.graph[s1][s2]['dst_port']
            p[path[-1]] = (in_port, out_port_dst_sw)
            paths_p.append(p)
        return paths_p
    
    # Добавление потока в коммутатор
    def install_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    # Нормализация стоимости путей
    def normalize(self, paths_weights):
        paths_weights = [MAX_VALUE if item == 0 else 1/item for item in paths_weights]
        total = sum(paths_weights)
        weights_after_normalizing = [round(float(i)/total, 2) for i in paths_weights]
        weights_after_normalizing[-1] += 1 - sum(weights_after_normalizing)
        weights_after_normalizing[-1] = round(weights_after_normalizing[-1], 2)
        return weights_after_normalizing

    # Получение оптимальных путей для пакетов
    def calculate_best_paths(self, src, dst):
        metric = copy.deepcopy(self.port_monitor.get_link_costs())
        for u in metric:
            for v in metric[u]:
                metric[u][v] = 1
        alg = Yen(metric, src, dst, K, same_cost=True)
        paths_nodes, paths_edges, paths_weights = alg.compute_shortest_paths()
        return paths_nodes, paths_edges, paths_weights
    
class NetworkStatRest(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(NetworkStatRest, self).__init__(req, link, data, **config)
        self.app: MultiPathLoadBalancing = data['rest_api_app']

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

    @route('rest_api_app', '/cost_2', methods=['GET'])
    def get_link_costs_2(self, req, **kwargs):
        cost_2 = self.app.port_monitor.get_link_costs_2()
        body = json.dumps(cost_2)
        return Response(content_type='application/json', body=body, status=200)
    
    @route('rest_api_app', '/rm_bw', methods=['GET'])
    def get_rm_bw(self, req, **kwargs):
        rm_bw = self.app.port_monitor.get_remaining_bandwidth()
        body = json.dumps(rm_bw)
        return Response(content_type='application/json', body=body, status=200)
    
    @route('rest_api_app', '/paths', methods=['GET'])
    def get_paths(self, req, **kwargs):
        paths_cache = {}
        if len(self.app.paths_cache) != 0:
            i = 0
            for key, item in self.app.paths_cache.items():
                if 'udp' in key:
                    itm = item[:(len(item)-1)]
                    paths_cache[i] = itm
                    i += 1
        body = json.dumps(paths_cache)
        return Response(content_type='application/json', body=body, status=200)