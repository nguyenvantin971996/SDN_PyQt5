# Импорт библиотек для работы с Ryu, OpenFlow и LLDP
from __future__ import division
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.topology.switches import Switches, LLDPPacket
import time
from setting import DELAY_PERIOD
from topology_monitor import TopologyMonitor

# Инициализация приложения DelayMonitor с атрибутами для мониторинга задержек
class DelayMonitor(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        # Инициализация приложения DelayMonitor
        super(DelayMonitor, self).__init__(*args, **kwargs)
        self.name = 'delay_monitor'  # Название приложения
        self.topology_monitor: TopologyMonitor = lookup_service_brick('topology_monitor')  # Мониторинг топологии
        self.sw_module: Switches = lookup_service_brick('switches')  # Модуль переключателей
        self.echo_latency = {}  # Словарь для хранения задержек echo-запросов
        self.latencies = {}  # Словарь для хранения задержек каналов
        self.sending_echo_request_interval = 0.05  # Интервал между echo-запросами
        self.monitor_thread = hub.spawn(self.monitor)  # Запуск потока измерений

    # Основной цикл мониторинга задержек
    def monitor(self):
        while True:
            try:
                if self.wait_for_topology_monitor_ready():
                    self.send_echo_request()
                    self.create_link_latency()
                hub.sleep(DELAY_PERIOD)
            except Exception as e:
                self.logger.error("Error in monitoring loop: %s", str(e))
                continue
    
    # Проверка готовности мониторинга топологии
    def wait_for_topology_monitor_ready(self):
        
        if self.topology_monitor is None:
            return False

        if not self.topology_monitor.datapaths:
            return False

        if not hasattr(self.topology_monitor, 'graph') or not self.topology_monitor.graph:
            return False

        return True

    # Отправка echo-запросов для каждого коммутатора
    def send_echo_request(self):
        for datapath in list(self.topology_monitor.datapaths.values()):
            parser = datapath.ofproto_parser

            data_time = "%.12f" % time.time()
            byte_arr = bytearray(data_time.encode())

            echo_req = parser.OFPEchoRequest(datapath, data=byte_arr)
            datapath.send_msg(echo_req)

            hub.sleep(self.sending_echo_request_interval)

    # Обработка ответа на echo-запрос
    @set_ev_cls(ofp_event.EventOFPEchoReply, MAIN_DISPATCHER)
    def echo_reply_handler(self, ev):
        now_timestamp = time.time()
        try:
            latency = now_timestamp - eval(ev.msg.data)
            self.echo_latency[ev.msg.datapath.id] = latency
        except:
            return

    # Расчет общей задержки между двумя коммутаторами
    def calculate_latency(self, src, dst):
        try:
            fwd_delay = self.topology_monitor.graph[src][dst]['lldpdelay']
            re_delay = self.topology_monitor.graph[dst][src]['lldpdelay']
            src_latency = self.echo_latency[src]
            dst_latency = self.echo_latency[dst]
            latency = round((fwd_delay + re_delay - src_latency - dst_latency) * 1000 / 2)
            return max(latency, 0)
        except:
            return None

    # Создание и обновление задержек каналов между коммутаторами
    def create_link_latency(self):
        new_latencies = {}
        for src in self.topology_monitor.graph:
            new_latencies.setdefault(src, {})
            for dst in self.topology_monitor.graph[src]:
                new_latencies[src].setdefault(dst, {})
                if src == dst:
                    continue
                latency = self.calculate_latency(src, dst)
                new_latencies[src][dst] = latency
        if new_latencies:
            self.latencies.update(new_latencies)

    # Обработка входящих пакетов, особенно для обработки LLDP
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        try:
            src_dpid, src_port_no = LLDPPacket.lldp_parse(msg.data)
            dpid = msg.datapath.id

            if self.sw_module is None:
                self.sw_module = lookup_service_brick('switches')

            for port in self.sw_module.ports.keys():
                if src_dpid == port.dpid and src_port_no == port.port_no:
                    delay = self.sw_module.ports[port].delay
                    self.save_lldp_delay(src=src_dpid, dst=dpid, lldpdelay=delay)
                    
        except LLDPPacket.LLDPUnknownFormat as e:
            return

    # Сохранение задержки LLDP между двумя коммутаторами
    def save_lldp_delay(self, src=0, dst=0, lldpdelay=0):
        try:
            self.topology_monitor.graph[src][dst]['lldpdelay'] = lldpdelay
        except:
            if self.topology_monitor is None:
                self.topology_monitor = lookup_service_brick('topology_monitor')
            return

    # Получение данных о задержках
    def get_latency(self):
        return self.latencies