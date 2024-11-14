from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, arp, tcp, udp, ethernet, ipv4, ipv6
from ryu import cfg
from ryu.lib import hub
from ryu.app.wsgi import WSGIApplication, ControllerBase, Response, route

import json
from decimal import Decimal
import copy
from itertools import combinations
from setting import REROUTING_PERIOD, K, MAX_CAPACITY

from delay_monitor import DelayMonitor
from port_monitor import PortMonitor
from topology_monitor import TopologyMonitor
from flow_monitor import FlowMonitor

from YenAlgorithm import YenAlgorithm
from ABC_static import ABC
from BFA_static import BFA
from FA_static import FA
from AS_static import AS
from ACS_static import ACS
from GA_static import GA

CONF = cfg.CONF

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
        self.WRR = {}

        # Запуск фоновой задачи для маршрутизации
        self.adaptive_routing_thread = hub.spawn(self.adaptive_routing)

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
            self.install_flow(datapath, 1, match, actions)
            return None

        mac_src = eth.src
        mac_dst = eth.dst
        dpid = datapath.id
        if mac_src not in self.hosts_map:
            self.hosts_map[mac_src] = (dpid, in_port)
        out_port = ofproto.OFPP_FLOOD

        # Обработка ARP-запросов и ответов
        if arp_pkt:
            src_ip = arp_pkt.src_ip
            dst_ip = arp_pkt.dst_ip
            if arp_pkt.opcode == arp.ARP_REQUEST:
                if dst_ip in self.ip_to_mac_map:
                    self.ip_to_mac_map[src_ip] = mac_src
                    dst_mac = self.ip_to_mac_map[dst_ip]
                    src_sw_in_port = self.hosts_map[mac_src]
                    dst_sw_in_port = self.hosts_map[dst_mac]
                    paths_nodes, _, _ = self.calculate_best_paths(src_sw_in_port[0], dst_sw_in_port[0])
                    out_port = self.set_paths_arp_icmp(src_sw_in_port[0], src_sw_in_port[1], dst_sw_in_port[0], dst_sw_in_port[1], src_ip, dst_ip, paths_nodes)

                    paths_reverse, _, _ = self.calculate_best_paths(dst_sw_in_port[0], src_sw_in_port[0])
                    self.set_paths_arp_icmp(dst_sw_in_port[0], dst_sw_in_port[1], src_sw_in_port[0], src_sw_in_port[1], dst_ip, src_ip, paths_reverse)

            elif arp_pkt.opcode == arp.ARP_REPLY:
                self.ip_to_mac_map[src_ip] = mac_src
                src_sw_in_port = self.hosts_map[mac_src]
                dst_sw_in_port = self.hosts_map[mac_dst]
                paths_nodes, _, _ = self.calculate_best_paths(src_sw_in_port[0], dst_sw_in_port[0])
                out_port = self.set_paths_arp_icmp(src_sw_in_port[0], src_sw_in_port[1], dst_sw_in_port[0], dst_sw_in_port[1], src_ip, dst_ip, paths_nodes)

                paths_reverse, _, _ = self.calculate_best_paths(dst_sw_in_port[0], src_sw_in_port[0])
                self.set_paths_arp_icmp(dst_sw_in_port[0], dst_sw_in_port[1], src_sw_in_port[0], src_sw_in_port[1], dst_ip, src_ip, paths_reverse)

            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(
                datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                actions=actions, data=data)
            datapath.send_msg(out)

        # Обработка TCP и UDP пакетов
        if tcp_pkt or udp_pkt:
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            src_sw_in_port = self.hosts_map[mac_src]
            dst_sw_in_port = self.hosts_map[mac_dst]     
            proto_type = 'tcp' if tcp_pkt else 'udp'
            key = (src_sw_in_port[0], src_sw_in_port[1], dst_sw_in_port[0], dst_sw_in_port[1], proto_type)
            if key not in list(self.paths_cache.keys()):
                paths_nodes, paths_edges, paths_weights = self.calculate_best_paths(src_sw_in_port[0], dst_sw_in_port[0])
                normalized_weights = self.normalize(paths_weights)
                weights = [int(round(i*10)) for i in normalized_weights]
                src_dst = f"Using DAMLB: {proto_type.upper()} {src_ip} --> {dst_ip}"
                streams = []
                self.WRR[key] = 1
                initial_index = self.weighted_periodic_distribution(weights, 1)
                streams.append((initial_index, tcp_pkt, udp_pkt))
                self.paths_cache[key] = [paths_nodes, paths_edges, paths_weights, src_ip, dst_ip, src_dst, streams]
                out_port = self.set_paths_tcp_udp(src_sw_in_port[0], src_sw_in_port[1], dst_sw_in_port[0], dst_sw_in_port[1], src_ip, dst_ip, paths_nodes, normalized_weights, initial_index, tcp_pkt, udp_pkt)

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
                normalized_weights = self.normalize(paths_weights)
                weights = [int(round(i*10)) for i in normalized_weights]
                self.WRR[key] += 1
                next_index = self.weighted_periodic_distribution(weights, self.WRR[key])
                self.paths_cache[key][-1].append((next_index, tcp_pkt, udp_pkt))
                out_port = self.set_paths_tcp_udp(src_sw_in_port[0], src_sw_in_port[1], dst_sw_in_port[0], dst_sw_in_port[1], src_ip, dst_ip, paths_nodes, normalized_weights, next_index, tcp_pkt, udp_pkt)
                
                actions = [parser.OFPActionOutput(out_port)]
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                    actions=actions, data=data)
                datapath.send_msg(out)

    # Установка путей для ARP и ICMP
    def set_paths_arp_icmp(self, src, in_port_src_sw, dst, out_port_dst_sw, ip_src, ip_dst, paths_nodes):
        paths_with_ports = self.paths_ports(paths_nodes, in_port_src_sw, out_port_dst_sw)
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
            self.install_flow(dp, 1, match_ip, actions)
            self.install_flow(dp, 1, match_arp, actions)
        return selected_path[src][1]
    
    # Удаление потоков по IP для TCP и UDP
    def delete_paths_tcp_udp(self, src, in_port_src_sw, dst, out_port_dst_sw, ip_src, ip_dst, paths_nodes, paths_weights, index, tcp_pkt, udp_pkt):
        paths_with_ports = self.paths_ports(paths_nodes, in_port_src_sw, out_port_dst_sw)
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
            self.delete_flow(dp, match_ip, out_port)
        return
    
    # Установка потоков по IP для TCP и UDP
    def set_paths_tcp_udp(self, src, in_port_src_sw, dst, out_port_dst_sw, ip_src, ip_dst, paths_nodes, paths_weights, index, tcp_pkt, udp_pkt):
        paths_with_ports = self.paths_ports(paths_nodes, in_port_src_sw, out_port_dst_sw)
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
            self.install_flow(dp, 32768, match_ip, actions)
        return selected_path[src][1]

    # Фоновая задача для обновления маршрутов
    def adaptive_routing(self):
        while True:
            metric = copy.deepcopy(self.port_monitor.get_link_costs())
            self.rerouting(metric)# Переназначение маршрутов
            self.update_weights_of_paths_cache(metric)# Обновление стоимости путей
            hub.sleep(REROUTING_PERIOD)

    # Функция переназначения маршрутов при перегрузке
    def rerouting(self, metric):
        overloaded_links = self.get_overloaded_links(metric)
        if len(overloaded_links)!=0:
            flows_overloaded = self.get_flows_overloaded(overloaded_links)
            new_metric = self.get_costs_to_adapt(flows_overloaded, metric)
            tmp_paths_dict = copy.deepcopy(self.paths_cache)
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
                    if flow in flows_overloaded:
                        streams_overloaded.append((path_index, tcp_pkt, udp_pkt))
                        if path_index not in paths_rerouting_index:
                            paths_rerouting_index.append(path_index)
                src = key[0]
                in_port_src_sw = key[1]
                dst = key[2]
                out_port_dst_sw = key[3]
                new_k = len(paths_rerouting_index)
                # Выбор алгоритма маршрутизации
                alg = YenAlgorithm(new_metric, src, dst, new_k)
                # alg = ABC(new_metric, src, dst, new_k, 10, 100, 20)
                # alg = ACS(new_metric, src, dst, new_k, 10, 100, 0.1, 1, 2, 0.5, 1)
                # alg = AS(new_metric, src, dst, new_k, 10, 100, 0.1, 1, 2, 1)
                # alg = BFA(new_metric, src, dst, new_k, 10, 100, 0.7, 2, 2)
                # alg = FA(new_metric, src, dst, new_k, 10, 100, 1, 1, 1)
                # alg = GA(new_metric, src, dst, new_k, 10, 100, 0.7, 0.7, 2)
                new_paths, new_paths_edges, new_pw = alg.compute_shortest_paths()
                paths_nodes, paths_edges, paths_weights, x1, x2, x3, x4 = copy.deepcopy(path_info)
                for idx in range(len(paths_rerouting_index)):
                    x = paths_rerouting_index[idx]
                    paths_nodes[x] = copy.deepcopy(new_paths[idx])
                    paths_edges[x] = copy.deepcopy(new_paths_edges[idx])
                paths_weights = self.calculate_weights_of_paths(metric, paths_edges)
                self.paths_cache[key][0] = paths_nodes
                self.paths_cache[key][1] = paths_edges
                self.paths_cache[key][2] = paths_weights
                normalize_pw = self.normalize(paths_weights)
                old_normalize_pw = self.normalize(old_pw)
                for path_index, tcp_pkt, udp_pkt in streams_overloaded:
                    self.delete_paths_tcp_udp(src, in_port_src_sw, dst, out_port_dst_sw, src_ip, dst_ip,
                                        old_paths, old_normalize_pw, path_index, tcp_pkt, udp_pkt)
                    self.set_paths_tcp_udp(src, in_port_src_sw, dst, out_port_dst_sw, src_ip, dst_ip,
                                        paths_nodes, normalize_pw, path_index, tcp_pkt, udp_pkt)

    # Получение списка перегруженных каналов (где стоимость канала >= 100)
    def get_overloaded_links(self, metric):
        overloaded_links = []
        for src in metric:
            for dst in metric[src]:
                link_cost = metric[src][dst]
                if link_cost is not None and link_cost > Decimal('10'):
                    overloaded_links.append((src, dst))
        return overloaded_links
    
    # Получение перегруженных потоков, проходящих через перегруженные каналы
    def get_flows_overloaded(self, overloaded_links):
        capacity = MAX_CAPACITY
        all_flows = self.get_all_flows_on_overloaded_links(overloaded_links)
        optimal_flow_set = self.find_minimal_flow_set(all_flows, overloaded_links, capacity)
        return set(optimal_flow_set) if optimal_flow_set else set()
    
    # Получение всех потоков, проходящих через перегруженные каналы
    def get_all_flows_on_overloaded_links(self, overloaded_links):
        all_flows = set()
        for src, dst in overloaded_links:
            if src in self.flow_monitor.switch_to_switch_flows_speed:
                if dst in self.flow_monitor.switch_to_switch_flows_speed[src]:
                    for key_flow in self.flow_monitor.switch_to_switch_flows_speed[src][dst].keys():
                        if key_flow[0] == 17:
                            all_flows.add(key_flow)
        return list(all_flows)

    # Поиск минимального множества потоков, удаление которых решает проблему перегрузки
    def find_minimal_flow_set(self, all_flows, overloaded_links, capacity):
        valid_flow_sets = []
        for r in range(1, len(all_flows) + 1):
            for subset in combinations(all_flows, r):
                if self.is_valid_solution(subset, overloaded_links, capacity):
                    total_speed = self.calculate_total_speed(subset, overloaded_links)
                    valid_flow_sets.append((subset, total_speed))
        valid_flow_sets.sort(key=lambda x: (len(x[0]), -x[1]))
        return valid_flow_sets[0][0] if valid_flow_sets else None

    # Проверка, что удаление указанного множества потоков решает проблему перегрузки
    def is_valid_solution(self, flow_subset, overloaded_links, capacity):
        for src, dst in overloaded_links:
            remaining_speed = sum(
                                speed for flow, speed in self.flow_monitor.switch_to_switch_flows_speed[src][dst].items()
                                if flow not in flow_subset
                                )        
            link_utilization = round(remaining_speed/capacity, 1)
            link_cost = None
            if link_utilization >= 1:
                link_cost = Decimal('100')
            else:
                link_cost= Decimal(str(round(1 / (1 - link_utilization), 1)))
            if link_cost > Decimal('10'):
                return False
        return True
    
    # Вычисление общей скорости для множества потоков
    def calculate_total_speed(self, flow_subset, overloaded_links):
        total_speed = 0
        for src, dst in overloaded_links:
            flow_speeds = self.flow_monitor.switch_to_switch_flows_speed[src][dst]
            total_speed += sum(flow_speeds[flow] for flow in flow_subset if flow in flow_speeds)
        return total_speed

    # Вычисление стоимости каналов для перегруженных потоков
    def get_costs_to_adapt(self, flows_overloaded, metric):
        capacity = MAX_CAPACITY
        new_metric = copy.deepcopy(metric)
        for src in self.flow_monitor.switch_to_switch_flows_speed:
            for dst in self.flow_monitor.switch_to_switch_flows_speed[src]:
                flows = set(self.flow_monitor.switch_to_switch_flows_speed[src][dst].keys())
                remain_flows = flows - flows_overloaded
                if len(flows & flows_overloaded)!=0:
                    remaining_speed = sum(self.flow_monitor.switch_to_switch_flows_speed[src][dst][flow_key] for flow_key in remain_flows)
                    link_utilization = round(remaining_speed/capacity, 1)
                    if link_utilization >= 1:
                        new_metric[src][dst] = Decimal('100')
                    else:
                        new_metric[src][dst] = Decimal(str(round(1 / (1 - link_utilization), 1)))
        return new_metric

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

    # Удаление потока
    def delete_flow(self, datapath, match, out_port):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE,
                                out_port=out_port, match=match)
        datapath.send_msg(mod)
    
    # Добавление потока в коммутатор
    def install_flow(self, datapath, priority, match, actions, buffer_id=None):
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

    # Вычисление стоимости путей
    def calculate_weights_of_paths(self, metric, paths_edges):
        paths_weights = []
        for path_edges in paths_edges:
            length = 0
            for edge in path_edges:
                u = edge[0]
                v = edge[1]
                length += metric[u][v]
            paths_weights.append(float(length))
        return paths_weights

    # Нормализация стоимости путей
    def normalize(self, paths_weights):
        paths_weights = [100 if item == 0 else 1/item for item in paths_weights]
        total = sum(paths_weights)
        weights_after_normalizing = [round(float(i)/total, 2) for i in paths_weights]
        weights_after_normalizing[-1] += 1 - sum(weights_after_normalizing)
        weights_after_normalizing[-1] = round(weights_after_normalizing[-1], 2)
        return weights_after_normalizing

    # Обновление стоимости путей
    def update_weights_of_paths_cache(self, metric):
        tmp_paths_dict = copy.deepcopy(self.paths_cache)
        for key, path_info in tmp_paths_dict.items():
            paths_nodes, paths_edges, paths_weights, x1, x2, x3, x4 = copy.deepcopy(path_info)
            new_pw = self.calculate_weights_of_paths(metric, paths_edges)
            self.paths_cache[key][2] = new_pw

    # Выбор элемента на основе весов
    def weighted_periodic_distribution(self, weights, n):
        if n <= 0:
            return None
        total_weights = sum(weights)
        if n > total_weights:
            n = n % total_weights
            if n == 0:
                n = total_weights
        current_pick = 0
        while sum(weights) > 0:
            for i in range(len(weights)):
                if weights[i] > 0:
                    current_pick += 1
                    weights[i] -= 1
                    if current_pick == n:
                        return i
        return None

    # Получение оптимальных путей для пакетов
    def calculate_best_paths(self, src, dst):
        metric = copy.deepcopy(self.port_monitor.get_link_costs())
        alg = YenAlgorithm(metric, src, dst, K)
        paths_nodes, paths_edges, paths_weights = alg.compute_shortest_paths()
        return paths_nodes, paths_edges, paths_weights
    
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
                    itm = item[:6]
                    paths_cache[i] = itm
                    i += 1
        body = json.dumps(paths_cache)
        return Response(content_type='application/json', body=body, status=200)