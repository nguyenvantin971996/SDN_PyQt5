# Импорт библиотек для работы с Ryu, потоками и вычислениями
from __future__ import division
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.base.app_manager import lookup_service_brick
from setting import FLOW_PERIOD

# Инициализация приложения FlowMonitor с атрибутами для мониторинга потоков между коммутаторами
class FlowMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        # Инициализация атрибутов для хранения статистики потоков и скорости
        super(FlowMonitor, self).__init__(*args, **kwargs)
        self.name = 'flow_monitor'  # Название приложения
        self.topology_monitor = lookup_service_brick('topology_monitor')  # Мониторинг топологии
        self.flow_stats = {}  # Статистика потоков
        self.switch_to_switch_flows = {}  # Потоки между коммутаторами
        self.switch_to_switch_flows_speed = {}  # Скорость потоков между коммутаторами
        self.monitor_thread = hub.spawn(self.monitor)  # Запуск мониторинга в отдельном потоке

    # Основной цикл мониторинга, который собирает статистику потоков
    def monitor(self):
        while True:
            try:
                if self.wait_for_topology_monitor_ready():
                    self.collect_stats()
                hub.sleep(FLOW_PERIOD)
            except Exception as e:
                self.logger.error("Error in monitoring loop: %s", str(e))
                continue

    # Проверка готовности монитора топологии
    def wait_for_topology_monitor_ready(self):
        
        if self.topology_monitor is None:
            return False

        if not self.topology_monitor.datapaths:
            return False

        if not hasattr(self.topology_monitor, 'graph') or not self.topology_monitor.graph:
            return False

        return True
    
    # Сбор статистики потоков
    def collect_stats(self):
        for datapath in self.topology_monitor.datapaths.values():
            self.request_stats(datapath)

    # Отправка запроса статистики потоков к коммутатору
    def request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    # Обработка ответа на запрос статистики потоков
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id

        self.flow_stats.setdefault(dpid, {}) 
        self.switch_to_switch_flows.setdefault(dpid, {})
        self.switch_to_switch_flows_speed.setdefault(dpid, {})
        
        for stat in sorted([flow for flow in body if flow.priority == 32768 and flow.match.get],
                           key=lambda flow: (flow.match.get('in_port'), flow.instructions[0].actions[0].port)):

            out_port = stat.instructions[0].actions[0].port

            key = (stat.match.get('ip_proto'), stat.match.get('ipv4_src'), stat.match.get('ipv4_dst'),
                   stat.match.get('tcp_src'), stat.match.get('udp_src'))

            value = (stat.packet_count, stat.byte_count,
                     stat.duration_sec, stat.duration_nsec)
            
            dst_switch = self.get_dst_switch(dpid, out_port)

            if dst_switch:
                if dst_switch not in self.switch_to_switch_flows[dpid]:
                    self.switch_to_switch_flows[dpid].setdefault(dst_switch, {})
                    self.switch_to_switch_flows_speed[dpid].setdefault(dst_switch, {})

                self.store_stats(self.switch_to_switch_flows[dpid][dst_switch], key, value, 5)
                self.calculate_flow_speed(key, dpid, dst_switch)

            self.store_stats(self.flow_stats[dpid], key, value, 5)

    # Расчет скорости потока на основе статистики
    def calculate_flow_speed(self, key, src, dst):
        pre = 0
        period = 0
        flow_stat_history = self.switch_to_switch_flows[src][dst][key]
        if len(flow_stat_history) > 1:
            pre = flow_stat_history[-2][1]
            period = self.calculate_period(
                flow_stat_history[-1][2], flow_stat_history[-1][3],
                flow_stat_history[-2][2], flow_stat_history[-2][3]
            )

        now = flow_stat_history[-1][1] if flow_stat_history else 0
        speed = round(self.calculate_speed(now, pre, period), 1)

        self.switch_to_switch_flows_speed[src][dst][key] = speed

    # Хранение статистики портов в истории
    def store_stats(self, stats_dict, key, value, length):
        if key not in stats_dict:
            stats_dict[key] = []
        stats_dict[key].append(value)
        if len(stats_dict[key]) > length:
            stats_dict[key].pop(0)

    # Расчет периода времени между двумя запросами статистики
    def calculate_period(self, n_sec, n_nsec, p_sec, p_nsec):
        return self.get_time(n_sec, n_nsec) - self.get_time(p_sec, p_nsec)

    # Преобразование времени в секундах и наносекундах в секунды
    def get_time(self, sec, nsec):
        return sec + nsec / (10 ** 9)

    # Расчет скорости передачи данных
    def calculate_speed(self, now, pre, period):
        if period:
            return 8 * (now - pre) / (period * 10 ** 6)
        else:
            return 0.0

    # Получение коммутатора назначения на основе порта выхода
    def get_dst_switch(self, src_dpid, out_port):
        if src_dpid in self.topology_monitor.graph:
            for dst_dpid in self.topology_monitor.graph[src_dpid]:
                link = self.topology_monitor.graph[src_dpid][dst_dpid]
                if link['src_port'] == out_port:
                    return dst_dpid
        return None
    
    # def show(self, src, dst):
    #     if src in self.switch_to_switch_flows_speed:
    #         if dst in self.switch_to_switch_flows_speed[src]:
    #             for key in self.switch_to_switch_flows_speed[src][dst].keys():
    #                 if key[0] == 17:
    #                     print((src, dst), self.switch_to_switch_flows_speed[src][dst][key])