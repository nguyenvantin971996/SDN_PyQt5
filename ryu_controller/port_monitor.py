from __future__ import division
from operator import attrgetter
from ryu import cfg
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from math import pow
from ryu.base.app_manager import lookup_service_brick
from decimal import Decimal
import setting
import json
import time

CONF = cfg.CONF

class PortMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PortMonitor, self).__init__(*args, **kwargs)
        self.name = 'port_monitor'
        self.topology_monitor = lookup_service_brick('topology_monitor')
        self.port_stats = {}
        self.port_features = {}
        self.throughputs = {}
        self.remaining_bandwidths = {}
        self.link_utilizations = {}
        self.link_costs = {}
        self.stats_reply_event = hub.Event()
        self.outstanding_requests = 0
        self.lbi_history = []
        self.monitor_thread = hub.spawn(self._monitor)

    def _monitor(self):
        while True:
            try:
                if self._wait_for_topology_monitor_ready():
                    self.collect_stats()
                    self.update_link_metrics()

                    lbi = self.get_load_balancing_index()
                    if lbi is not None and len(self.lbi_history) < 60:
                        self.lbi_history.append(lbi)
                    if len(self.lbi_history) == 60 :
                        self.save_lbi_history_to_json("result/Round_Robin.json")

                hub.sleep(setting.MONITOR_PERIOD)
            except Exception as e:
                self.logger.error("Error in monitoring loop: %s", str(e))
                continue
    
    def save_lbi_history_to_json(self, file_name="result/lbi_history.json"):
        with open(file_name, 'w') as json_file:
            json.dump(self.lbi_history, json_file, indent=4)

    def calculate_load_balancing_index(self, utilizations):
        if not utilizations or len(utilizations) == 0:
            return None

        n = len(utilizations)
        sum_utilization = sum(utilizations)
        sum_square_utilization = sum([pow(u, 2) for u in utilizations])

        if sum_square_utilization == 0:
            return 1

        lbi = pow(sum_utilization, 2) / (n * sum_square_utilization)
        return lbi

    def get_load_balancing_index(self):
        utilizations = []
        for src in self.link_utilizations:
            for dst in self.link_utilizations[src]:
                utilization = self.link_utilizations[src][dst]
                if utilization is not None:
                    utilizations.append(utilization)

        return self.calculate_load_balancing_index(utilizations)

    def _wait_for_topology_monitor_ready(self):
        if self.topology_monitor is None:
            return False

        if not self.topology_monitor.datapaths:
            return False

        if not hasattr(self.topology_monitor, 'graph') or not self.topology_monitor.graph:
            return False

        return True
    
    
    def collect_stats(self):
        self.stats_reply_event.clear()
        self.throughputs = {}
        self.remaining_bandwidths = {}
        self.link_utilizations = {}

        for datapath in self.topology_monitor.datapaths.values():
            self.port_features.setdefault(datapath.id, {})
            self._request_stats(datapath)
            
        if not self.stats_reply_event.wait(timeout=setting.time_out):
            self.logger.warning("Stats reply timed out.")
            return

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPPortDescStatsRequest(datapath, 0)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

        self.outstanding_requests += 2

    def update_link_metrics(self):
        capacity = setting.MAX_CAPACITY
        new_link_costs = {}

        for src in self.topology_monitor.graph:
            self.remaining_bandwidths.setdefault(src, {})
            self.link_utilizations.setdefault(src, {})
            new_link_costs.setdefault(src, {})
            for dst in self.topology_monitor.graph[src]:
                if src != dst:
                    self.remaining_bandwidths[src].setdefault(dst, {})
                    self.link_utilizations[src].setdefault(dst, {})
                    new_link_costs[src].setdefault(dst, {})

                    speed = self.throughputs.get(src, {}).get(dst, 0)
                    free_bandwidth = self.calculate_free_bandwidth(capacity, speed)
                    self.remaining_bandwidths[src][dst] = free_bandwidth
                    link_utilization = round(speed / capacity, 1)

                    if self.topology_monitor.graph[src][dst]['status'] == 'down':
                        link_utilization = None

                    self.link_utilizations[src][dst] = link_utilization

                    if link_utilization == None:
                        new_link_costs[src][dst] = Decimal('1000')
                    elif link_utilization == 1:
                        new_link_costs[src][dst] = Decimal('100')
                    else:
                        new_link_costs[src][dst] = Decimal(str(round(1 / (1 - link_utilization), 1)))

        if new_link_costs:
            self.link_costs.clear()
            self.link_costs.update(new_link_costs)

    def calculate_free_bandwidth(self, capacity, speed):
        return max(capacity - speed, 0)

    def store_stats(self, stats_dict, key, value, length):
        if key not in stats_dict:
            stats_dict[key] = []
        stats_dict[key].append(value)

        if len(stats_dict[key]) > length:
            stats_dict[key].pop(0)

    def calculate_port_speed(self, key):
        pre = 0
        period = 0
        port_stat_history = self.port_stats.get(key, [])
        if len(port_stat_history) > 1:
            pre = port_stat_history[-2][0]
            period = self._calculate_period(
                port_stat_history[-1][3], port_stat_history[-1][4],
                port_stat_history[-2][3], port_stat_history[-2][4]
            )

        now = port_stat_history[-1][0] if port_stat_history else 0
        speed = round(self._calculate_speed(now, pre, period), 1)
        src = key[0]

        for dst in self.topology_monitor.graph[src]:
            if self.topology_monitor.graph[src][dst]['src_port'] == key[1]:
                self.throughputs[src].setdefault(dst, {})
                self.throughputs[src][dst] = speed
                break

    def _calculate_period(self, n_sec, n_nsec, p_sec, p_nsec):
        return self._get_time(n_sec, n_nsec) - self._get_time(p_sec, p_nsec)

    def _get_time(self, sec, nsec):
        return sec + nsec / (10 ** 9)

    def _calculate_speed(self, now, pre, period):
        if period:
            return 8 * (now - pre) / (period * 10 ** 6)
        else:
            return 0.0

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id

        self.throughputs.setdefault(dpid, {})

        for stat in sorted(body, key=attrgetter('port_no')):
            port_no = stat.port_no
            if port_no != ofproto_v1_3.OFPP_LOCAL:
                key = (dpid, port_no)
                value = (stat.tx_bytes, stat.rx_bytes, stat.rx_errors,
                         stat.duration_sec, stat.duration_nsec)
                self.store_stats(self.port_stats, key, value, 5)
                self.calculate_port_speed(key)

        self.outstanding_requests -= 1
        if self.outstanding_requests == 0:
            self.stats_reply_event.set()

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        msg = ev.msg
        dpid = msg.datapath.id

        for p in ev.msg.body:
            for dst in self.topology_monitor.graph[dpid]:
                if self.topology_monitor.graph[dpid][dst]['src_port'] == p.port_no:
                    self.port_features[dpid].setdefault(dst, {})
                    self.port_features[dpid][dst] = p.curr_speed / 1000  # Convert to Mbps
                    break

        self.outstanding_requests -= 1
        if self.outstanding_requests == 0:
            self.stats_reply_event.set()

    def get_throughput(self):
        return self.throughputs

    def get_remaining_bandwidth(self):
        return self.remaining_bandwidths

    def get_link_utilization(self):
        return self.link_utilizations

    def get_link_costs(self):
        return self.link_costs