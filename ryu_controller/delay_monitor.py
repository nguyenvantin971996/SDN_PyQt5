# Импорт библиотек для работы с Ryu, OpenFlow и LLDP
from __future__ import division
from ryu import cfg
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.topology.switches import Switches, LLDPPacket
import time
import setting
from topology_monitor import TopologyMonitor
CONF = cfg.CONF

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
        self.measure_thread = hub.spawn(self._detector)  # Запуск потока измерений

    # Основной цикл мониторинга задержек
    def _detector(self):
        while CONF.delay == 1:
            self._send_echo_request()
            self.create_link_latency()
            hub.sleep(setting.DELAY_DETECTING_PERIOD)

    # Отправка echo-запросов для каждого коммутатора
    def _send_echo_request(self):
        if self.topology_monitor is not None:
            try:
                for datapath in list(self.topology_monitor.datapaths.values()):
                    parser = datapath.ofproto_parser

                    # Временная метка для запроса
                    data_time = "%.12f" % time.time()
                    byte_arr = bytearray(data_time.encode())  # Преобразование в байтовый массив

                    echo_req = parser.OFPEchoRequest(datapath, data=byte_arr)
                    datapath.send_msg(echo_req)  # Отправка сообщения echo-запроса

                    hub.sleep(self.sending_echo_request_interval)  # Пауза между запросами
            
            except Exception as e:
                self.logger.error("Error sending echo request: %s", e)
        else:
            self.topology_monitor = lookup_service_brick('topology_monitor')
            return

    # Обработка ответа на echo-запрос
    @set_ev_cls(ofp_event.EventOFPEchoReply, MAIN_DISPATCHER)
    def echo_reply_handler(self, ev):
        now_timestamp = time.time()
        try:
            # Расчет задержки на основе времени запроса и ответа
            latency = now_timestamp - eval(ev.msg.data)
            self.echo_latency[ev.msg.datapath.id] = latency  # Сохранение задержки для коммутатора
        except:
            return

    # Расчет общей задержки между двумя коммутаторами
    def calculate_latency(self, src, dst):
        try:
            fwd_delay = self.topology_monitor.graph[src][dst]['lldpdelay']  # Прямая задержка LLDP
            re_delay = self.topology_monitor.graph[dst][src]['lldpdelay']  # Обратная задержка LLDP
            src_latency = self.echo_latency[src]  # Echo-задержка источника
            dst_latency = self.echo_latency[dst]  # Echo-задержка назначения

            # Общая задержка
            latency = round((fwd_delay + re_delay - src_latency - dst_latency) * 1000 / 2)
            return max(latency, 0)
        except:
            return float('inf')

    # Создание и обновление задержек каналов между коммутаторами
    def create_link_latency(self):
        try:
            for src in self.topology_monitor.graph:
                for dst in self.topology_monitor.graph[src]:
                    if src == dst:
                        continue
                    latency = self.calculate_latency(src, dst)  # Расчет задержки
                    if latency == float('inf'):
                        latency = None  # Если задержка не определена
                    self.topology_monitor.graph[src][dst]['latency'] = latency  # Сохранение задержки
        except:
            if self.topology_monitor is None:
                self.topology_monitor = lookup_service_brick('topology_monitor')
            return

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
                    self._save_lldp_delay(src=src_dpid, dst=dpid, lldpdelay=delay)
        except LLDPPacket.LLDPUnknownFormat as e:
            return

    # Сохранение задержки LLDP между двумя коммутаторами
    def _save_lldp_delay(self, src=0, dst=0, lldpdelay=0):
        try:
            self.topology_monitor.graph[src][dst]['lldpdelay'] = lldpdelay
        except:
            if self.topology_monitor is None:
                self.topology_monitor = lookup_service_brick('topology_monitor')
            return

    # Получение данных о задержках
    def get_latency(self):
        return self.latencies