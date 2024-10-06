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

# Импорт модулей для мониторинга задержек, портов и топологии
from delay_monitor import DelayMonitor
from port_monitor import PortMonitor
from topology_monitor import TopologyMonitor

CONF = cfg.CONF

# Импорт алгоритмов для маршрутизации
from YenAlgorithm import YenAlgorithm
from YenAlgorithm_dynamic import YenAlgorithm_dynamic
from ABC_dynamic import ABC
from BFA_dynamic import BFA
from FA_dynamic import FA
from AS_dynamic import AS
from ACS_dynamic import ACS
from GA_dynamic import GA

# Определение класса MultiPathRouting, который наследует RyuApp
class MultiPathRouting(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # Контексты для использования различных модулей
    _CONTEXTS = {
            'wsgi': WSGIApplication,
            'topology_monitor': TopologyMonitor,
            'port_monitor': PortMonitor,
            'delay_monitor': DelayMonitor,
        }

    # Инициализация класса
    def __init__(self, *_args, **_kwargs):

        super(MultiPathRouting, self).__init__(*_args, **_kwargs)
        self.name = 'multipath_routing'
        
        wsgi: WSGIApplication = _kwargs['wsgi']
        wsgi.register(NetworkStatRest, {'rest_api_app': self})

        # Инициализация мониторов
        self.topology_monitor: TopologyMonitor = _kwargs['topology_monitor']
        self.port_monitor: PortMonitor = _kwargs['port_monitor']
        self.delay_monitor: DelayMonitor = _kwargs['delay_monitor']
        
        # Таблицы для ARP и маршрутов
        self.arp_table = {}
        self.hosts = {}
        self.paths_dict = {}
        self.sw = 0
        self.sum_pw = {}
        self.t = 0
        
        # Запуск фоновых процессов
        self.routing_background_thread = hub.spawn(self.routing_background)
        self.get_sum_pw_thread = hub.spawn(self.get_sum_pw)

    # Фоновый процесс для обновления маршрутов
    def routing_background(self):
        while True:
            start_time = time.time()
            keys_list = []
            for key in list(self.paths_dict.keys()):
                    self.update_paths(key)
            end_time = time.time()
            execution_time = end_time - start_time
            sleep_time = max(UPDATE_PATHS_PERIOD - execution_time, 0)
            hub.sleep(sleep_time)
    
    # Фоновый процесс для вычисления суммы весов путей
    def get_sum_pw(self):
        metric = self.port_monitor.get_link_costs()
        while True:
            hub.sleep(1)
            self.t += 1
            if self.t > 25:
                for key, value in list(self.paths_dict.items()):
                    key_sum = value[3] + '-->' + value[4]
                    if key_sum not in self.sum_pw:
                        self.sum_pw[key_sum] = []
                    paths_pw = [self.compute_path_length(metric, path) for path in value[0]]
                    self.sum_pw[key_sum].append(sum(paths_pw))
            if self.t == 45:
                with open('/home/tin/SDN_PyQt5/result/Yen_dynamic.json', 'w') as f:
                    json.dump(self.sum_pw, f, indent=4)
    
    # Вычисление длины пути
    def compute_path_length(self, metric, path):
        path_length = 0
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            path_length += metric[u][v]
        return float(path_length)
    
    # Обновление путей на основе алгоритма маршрутизации
    def update_paths(self, key):
        # alg = YenAlgorithm_dynamic(self.port_monitor, self.paths_dict, key, K)
        alg = GA(self.port_monitor, self.paths_dict, key, K, 10, 100000, 0.7, 0.7, 2)
        # alg = ABC(self.port_monitor, self.paths_dict, key, K, 10, 100000, 20)
        # alg = BFA(self.port_monitor, self.paths_dict, key, K, 10, 100000, 0.7, 2, 2)
        # alg = AS(self.port_monitor, self.paths_dict, key, K, 10, 100000, 0.1, 1, 1, 0.5, 1)
        # alg = ACS(self.port_monitor, self.paths_dict, key, K, 10, 100000, 0.1, 1, 1, 0.5, 1)
        # alg = FA(self.port_monitor, self.paths_dict, key, K, 10, 100000, 1, 1, 1, True)
        alg.compute_shortest_paths(time_limit)

        src = key[0]
        first_port = key[1]
        dst = key[2]
        last_port = key[3]

        paths, paths_edges, pw, src_ip, dst_ip, src_dst, streams = self.paths_dict[key]

        normalize_pw = self.make_normalized(pw)

        for stream_index, tcp_pkt, udp_pkt in streams:
            self.install_paths_ip(src, first_port, dst, last_port, src_ip, dst_ip, paths, normalize_pw, stream_index, tcp_pkt, udp_pkt)

    # Получение оптимальных путей между двумя узлами
    def get_optimal_paths(self, src, dst):
        metric = self.port_monitor.get_link_costs()
        alg = YenAlgorithm(metric, src, dst, K)
        paths, paths_edges, pw = alg.compute_shortest_paths()
        return paths, paths_edges, pw
    
    # Нормализация весов путей
    def make_normalized(self, pw):
        pw = [100 if item == 0 else 1/item for item in pw]
        total = sum(pw)
        normalized_pw = [round(float(i)/total, 2) for i in pw]
        normalized_pw[-1] += 1 - sum(normalized_pw)
        normalized_pw[-1] = round(normalized_pw[-1], 2)
        return normalized_pw

    # Добавление портов к путям
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

    # Установка путей для ARP-запросов
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
    
    # Установка путей для IP пакетов (TCP/UDP)
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
            
            self.remove_flows(dp, match_ip)

            actions = [ofp_parser.OFPActionOutput(out_port)]    
            self.add_flow(dp, 32768, match_ip, actions)

        return selected_path[src][1]

    # Удаление потоков
    def remove_flows(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(datapath=datapath, command=ofproto.OFPFC_DELETE,
                                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                                match=match)
        datapath.send_msg(mod)
    
    # Добавление потоков в коммутатор
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

    # Обработчик функций коммутатора
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

    # Обработчик входящих пакетов (packet_in handler)
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # Получаем сообщение, содержащее данные о пакете и его пути
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']  # Порт, через который поступил пакет

        # Извлечение пакета и его различных протоколов
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)
        udp_pkt = pkt.get_protocol(udp.udp)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        # Игнорирование LLDP пакетов (Ethernet тип 35020)
        if eth.ethertype == 35020:
            return

        # Игнорирование пакетов IPv6
        if pkt.get_protocol(ipv6.ipv6):
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return None

        # Получение MAC-адресов источника и назначения
        src = eth.src
        dst = eth.dst

        # Определение идентификатора коммутатора
        dpid = datapath.id

        # Если источник не зарегистрирован в списке хостов, добавляем его
        if src not in self.hosts:
            self.hosts[src] = (dpid, in_port)

        # Изначально устанавливаем out_port как OFPP_FLOOD, чтобы "затопить" пакет, если путь не определён
        out_port = ofproto.OFPP_FLOOD

        # Обработка ARP пакетов
        if arp_pkt:
            src_ip = arp_pkt.src_ip  # IP источника
            dst_ip = arp_pkt.dst_ip  # IP назначения

            # Если это ARP-запрос
            if arp_pkt.opcode == arp.ARP_REQUEST:
                # Проверяем, есть ли IP назначения в ARP-таблице
                if dst_ip in self.arp_table:
                    # Добавляем MAC источника в ARP-таблицу
                    self.arp_table[src_ip] = src
                    # Находим MAC-адрес назначения
                    dst_mac = self.arp_table[dst_ip]

                    # Получаем коммутаторы для источника и назначения
                    h1 = self.hosts[src]
                    h2 = self.hosts[dst_mac]

                    # Получаем оптимальные пути между источником и назначением
                    paths, paths_edges, pw = self.get_optimal_paths(h1[0], h2[0])

                    # Нормализуем веса путей
                    normalize_pw = self.make_normalized(pw)

                    # Устанавливаем пути для ARP-запроса
                    out_port = self.install_paths_arp(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw)

                    # Устанавливаем обратные пути для ARP-ответа
                    paths_reverse, paths_edges_reverse, pw_reverse = self.get_optimal_paths(h2[0], h1[0])
                    normalize_pw_reverse = self.make_normalized(pw_reverse)
                    self.install_paths_arp(h2[0], h2[1], h1[0], h1[1], dst_ip, src_ip, paths_reverse, normalize_pw_reverse)

            # Если это ARP-ответ
            elif arp_pkt.opcode == arp.ARP_REPLY:
                # Добавляем MAC источника в ARP-таблицу
                self.arp_table[src_ip] = src

                # Получаем коммутаторы для источника и назначения
                h1 = self.hosts[src]
                h2 = self.hosts[dst]

                # Получаем оптимальные пути между источником и назначением
                paths, paths_edges, pw = self.get_optimal_paths(h1[0], h2[0])

                # Нормализуем веса путей
                normalize_pw = self.make_normalized(pw)

                # Устанавливаем пути для ARP-ответа
                out_port = self.install_paths_arp(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw)

                # Устанавливаем обратные пути для ARP-запроса
                paths_reverse, paths_edges_reverse, pw_reverse = self.get_optimal_paths(h2[0], h1[0])
                normalize_pw_reverse = self.make_normalized(pw_reverse)
                self.install_paths_arp(h2[0], h2[1], h1[0], h1[1], dst_ip, src_ip, paths_reverse, normalize_pw_reverse)

            # Формируем действия для выхода на определённый порт
            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data

            # Отправляем пакет с действиями
            out = parser.OFPPacketOut(
                datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                actions=actions, data=data)
            datapath.send_msg(out)

        # Обработка TCP и UDP пакетов
        if tcp_pkt or udp_pkt:
            # Извлекаем IP-адреса источника и назначения
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst

            # Получаем коммутаторы для источника и назначения
            h1 = self.hosts[src]
            h2 = self.hosts[dst]

            # Если пути между хостами еще не добавлены в словарь путей
            paths, paths_edges, pw = [], [], []
            if (h1[0], h1[1], h2[0], h2[1]) not in list(self.paths_dict.keys()):
                # Получаем оптимальные пути между источником и назначением
                paths, paths_edges, pw = self.get_optimal_paths(h1[0], h2[0])

                # Создаём запись о потоках
                src_dst = "Round Robin: " + src_ip + " --> " + dst_ip
                streams = []
                streams.append((0, tcp_pkt, udp_pkt))

                # Добавляем в словарь путей новую запись
                self.paths_dict[(h1[0], h1[1], h2[0], h2[1])] = [paths, paths_edges, pw, src_ip, dst_ip, src_dst, streams]

                # Нормализуем веса путей
                normalize_pw = self.make_normalized(pw)

                # Устанавливаем пути для IP пакетов (TCP/UDP)
                out_port = self.install_paths_ip(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw, 0, tcp_pkt, udp_pkt)

                # Формируем действия для выхода на определённый порт
                actions = [parser.OFPActionOutput(out_port)]
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                # Отправляем пакет с действиями
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                    actions=actions, data=data)
                datapath.send_msg(out)

            # Если пути уже существуют в словаре путей
            else:
                # Извлекаем информацию о путях и потоках из словаря
                [paths, paths_edges, pw, x1, x2, x3, streams] = self.paths_dict[(h1[0], h1[1], h2[0], h2[1])]

                # Определяем индекс следующего потока (для кругового распределения)
                index = streams[-1][0]
                next_index = (index+1)%len(paths)

                # Нормализуем веса путей
                normalize_pw = self.make_normalized(pw)

                # Устанавливаем пути для IP пакетов (TCP/UDP) на основе индекса
                out_port = self.install_paths_ip(h1[0], h1[1], h2[0], h2[1], src_ip, dst_ip, paths, normalize_pw, next_index, tcp_pkt, udp_pkt)

                # Обновляем запись о потоках
                self.paths_dict[(h1[0], h1[1], h2[0], h2[1])][-1].append((next_index, tcp_pkt, udp_pkt))

                # Формируем действия для выхода на определённый порт
                actions = [parser.OFPActionOutput(out_port)]
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                # Отправляем пакет с действиями
                out = parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                    actions=actions, data=data)
                datapath.send_msg(out)
    
# REST API для сетевой статистики
class NetworkStatRest(ControllerBase):

    # Конструктор для инициализации REST API с приложением MultiPathRouting
    def __init__(self, req, link, data, **config):
        super(NetworkStatRest, self).__init__(req, link, data, **config)
        self.app: MultiPathRouting = data['rest_api_app']

    # API для проверки соединения, возвращает приветственное сообщение
    @route('rest_api_app', '/', methods=['GET'])
    def hello(self, req, **_kwargs):
        body = json.dumps([{'hello': 'world'}])
        return Response(content_type='application/json', body=body, status=200)
    
    # API для получения топологии сети
    @route('rest_api_app', '/topology_graph', methods=['GET'])
    def get_topology_graph(self, req, **kwargs):
        graph = self.app.topology_monitor.get_topology_graph()
        body = json.dumps(graph)
        return Response(content_type='application/json', body=body, status=200)

    # API для получения задержек в сети
    @route('rest_api_app', '/latency', methods=['GET'])
    def get_latency(self, req, **kwargs):
        latency = self.app.delay_monitor.get_latency()
        body = json.dumps(latency)
        return Response(content_type='application/json', body=body, status=200)
    
    # API для получения информации о пропускной способности сети
    @route('rest_api_app', '/throughput', methods=['GET'])
    def get_throughput(self, req, **kwargs):
        throughput = self.app.port_monitor.get_throughput()
        body = json.dumps(throughput)
        return Response(content_type='application/json', body=body, status=200)
    
    # API для получения оставшейся пропускной способности (bw - bandwidth)
    @route('rest_api_app', '/rm_bw', methods=['GET'])
    def get_rm_bw(self, req, **kwargs):
        rm_bw = self.app.port_monitor.get_remaining_bandwidth()
        body = json.dumps(rm_bw)
        return Response(content_type='application/json', body=body, status=200)
    
    # API для получения информации о маршрутах
    @route('rest_api_app', '/paths', methods=['GET'])
    def get_paths(self, req, **kwargs):
        paths_dict = {}
        if len(self.app.paths_dict) != 0:
            i = 0
            for key, item in self.app.paths_dict.items():
                itm = item[:6]
                paths_dict[i] = itm
                i += 1
        body = json.dumps(paths_dict)
        return Response(content_type='application/json', body=body, status=200)