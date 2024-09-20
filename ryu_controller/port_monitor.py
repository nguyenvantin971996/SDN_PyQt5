from __future__ import division
from operator import attrgetter
from ryu import cfg
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.base.app_manager import lookup_service_brick

import setting
from topology_monitor import TopologyMonitor
from get_metric import getMetric
from decimal import Decimal
import time

CONF = cfg.CONF

class PortMonitor(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PortMonitor, self).__init__(*args, **kwargs)
        self.name = 'port_monitor'
        self.topology_monitor: TopologyMonitor = lookup_service_brick('topology_monitor')
        self.port_stats = {}
        self.port_features = {}
        self.throughputs = {}
        self.rm_bws = {}
        self.link_utilizations = {}
        self.link_costs = {}
        self.stats_reply_event = hub.Event()
        self.outstanding_requests = 0
        self.monitor_thread = hub.spawn(self._monitor)

    def _monitor(self):
        while True:
            try:
                self.get_inf()
                self.get_rm_bw_lu()
                hub.sleep(setting.MONITOR_PERIOD)
            except Exception as e:
                self.logger.error("Error in monitoring loop: %s", str(e))
                continue

    def get_inf(self):
        if self.topology_monitor is None:
            self.logger.warning("Topology monitor service is not available.")
            self.topology_monitor = lookup_service_brick('topology_monitor')
            if self.topology_monitor is None:
                self.logger.error("Failed to retrieve topology monitor service.")
                return

        self.stats_reply_event.clear()
        self.throughputs = {}
        self.rm_bws = {}
        self.link_utilizations = {}

        for dp in self.topology_monitor.datapaths.values():
            self.port_features.setdefault(dp.id, {})
            self._request_stats(dp)
            
        if not self.stats_reply_event.wait(timeout=setting.time_out):
            # self.logger.error("Timeout waiting for stats replies.")
            return


    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.outstanding_requests += 2

        req = parser.OFPPortDescStatsRequest(datapath, 0)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)


    def get_rm_bw_lu(self):
        capacity = setting.MAX_CAPACITY
        new_link_costs = {}
        for src in self.topology_monitor.graph:
            self.rm_bws.setdefault(src, {})
            self.link_utilizations.setdefault(src, {})
            new_link_costs.setdefault(src, {})
            for dst in self.topology_monitor.graph[src]:
                if src != dst:
                    self.rm_bws[src].setdefault(dst, {})
                    self.link_utilizations[src].setdefault(dst, {})
                    new_link_costs[src].setdefault(dst, {})
                    speed = self.throughputs[src][dst]
                    rm_bw = self.get_free_bw(capacity, speed)
                    self.rm_bws[src][dst]= rm_bw
                    LU = round(speed/capacity, 1)
                    if self.topology_monitor.graph[src][dst]['status'] == 'down':
                        LU = 10
                    self.link_utilizations[src][dst]= LU
                    if LU == 1:
                        new_link_costs[src][dst] = Decimal('10')
                    elif LU == 10:
                        new_link_costs[src][dst] = Decimal('10')
                    else:
                        new_link_costs[src][dst] = Decimal(str(round(1/(1 - LU), 1)))
        if new_link_costs:
            self.link_costs.clear()
            self.link_costs.update(new_link_costs)

    def get_free_bw(self, capacity, speed):
        return max(capacity - speed, 0)
    
    def save_stats(self, _dict, key, value, length):
        if key not in _dict:
            _dict[key] = []
        _dict[key].append(value)

        if len(_dict[key]) > length:
            _dict[key].pop(0)

    def get_port_speed(self, key):
        pre = 0
        period = 0
        tmp = self.port_stats[key]
        if len(tmp) > 1:
            # pre = tmp[-2][0] + tmp[-2][1]
            pre = tmp[-2][0]
            period = self.get_period(tmp[-1][3], tmp[-1][4],
                                        tmp[-2][3], tmp[-2][4])
            # if key == (2, 3):
            #     print(self.port_stats[key])
        # now = tmp[-1][0] + tmp[-1][1]
        now = tmp[-1][0]
        speed = round(self.get_speed(now, pre, period), 1)
        src = key[0]
        for dst in self.topology_monitor.graph[src]:
            if self.topology_monitor.graph[src][dst]['src_port']==key[1]:
                self.throughputs[src].setdefault(dst, {})
                self.throughputs[src][dst] = speed
                break

    def get_period(self, n_sec, n_nsec, p_sec, p_nsec):
        return self.get_time(n_sec, n_nsec) - self.get_time(p_sec, p_nsec)
    
    def get_time(self, sec, nsec):
        return sec + nsec / (10 ** 9)
    
    def get_speed(self, now, pre, period):
        if period:
            return 8*(now - pre) / (period*10**6)
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
                self.save_stats(self.port_stats, key, value, 5)
                self.get_port_speed(key)
        self.outstanding_requests -= 1
        if self.outstanding_requests == 0:
            self.stats_reply_event.set()

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        msg = ev.msg
        dpid = msg.datapath.id

        for p in ev.msg.body:
            for dst in self.topology_monitor.graph[dpid]:
                if self.topology_monitor.graph[dpid][dst]['src_port']==p.port_no:
                    self.port_features[dpid].setdefault(dst, {})
                    self.port_features[dpid][dst] = p.curr_speed/1000 #Mbps
                    break
        self.outstanding_requests -= 1
        if self.outstanding_requests == 0:
            self.stats_reply_event.set()
    
    def get_throughput(self):
        return self.throughputs
    
    def get_rm_bw(self):
        return self.rm_bws

    def get_link_utilization(self):
        return self.link_utilizations
    
    def get_link_costs(self):
        return self.link_costs