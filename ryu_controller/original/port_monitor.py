from __future__ import division
from audioop import avg
import copy
import numpy as np
from operator import attrgetter
from ryu import cfg
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet
import networkx as nx
from ryu.base.app_manager import lookup_service_brick
import setting
import json
from ryu.lib.packet import arp
from topology_monitor import TopologyMonitor

CONF = cfg.CONF

class PortMonitor(app_manager.RyuApp):
    """
        PortMonitor is a Ryu app for collecting traffic information.

    """
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
        self.monitor_thread = hub.spawn(self._monitor)
    
    def _monitor(self):
        """
            Main entry method of monitoring traffic.
        """
        while CONF.bw == 1:
            if self.topology_monitor is not None:
                try:
                    for dp in self.topology_monitor.datapaths.values():
                        self.port_features.setdefault(dp.id, {})
                        self._request_stats(dp)
                    self.get_rm_bw_lu()
                    hub.sleep(setting.MONITOR_PERIOD)
                except Exception as e:
                    self.logger.error("Error: %s", e)
            else:
                self.topology_monitor = lookup_service_brick('topology_monitor')
                return

    def _request_stats(self, datapath):
        """
            Sending request msg to datapath
        """
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPPortDescStatsRequest(datapath, 0)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)


    def get_rm_bw_lu(self):
        capacity = setting.MAX_CAPACITY
        for src in self.topology_monitor.graph:
            self.rm_bws.setdefault(src, {})
            self.link_utilizations.setdefault(src, {})
            for dst in self.topology_monitor.graph[src]:
                if src != dst:
                    self.rm_bws[src].setdefault(dst, {})
                    self.link_utilizations[src].setdefault(dst, {})
                    curr_bw = 0
                    speed = 0
                    try:
                        speed = self.throughputs[src][dst]
                        curr_bw = self.get_free_bw(capacity, speed)
                    except:
                        curr_bw = capacity
                    self.rm_bws[src][dst]= curr_bw
                    self.link_utilizations[src][dst]= round(speed/capacity, 1)

    def save_stats(self, _dict, key, value, length):
        if key not in _dict:
            _dict[key] = []
        _dict[key].append(value)

        if len(_dict[key]) > length:
            _dict[key].pop(0)

    def get_speed(self, now, pre, period):
        if period:
            return 8*(now - pre) / (period*10**6)
        else:
            return 0.0

    def get_free_bw(self, capacity, speed):
        # BW:Mbit/s
        return max(capacity - speed, 0)

    def get_time(self, sec, nsec):
        return sec + nsec / (10 ** 9)

    def get_period(self, n_sec, n_nsec, p_sec, p_nsec):
        return self.get_time(n_sec, n_nsec) - self.get_time(p_sec, p_nsec)
    
    def get_port_speed(self, key):
        pre = 0
        period = 0
        tmp = self.port_stats[key]
        if len(tmp) > 1:
            pre = tmp[-2][0]
            period = self.get_period(tmp[-1][3], tmp[-1][4],
                                        tmp[-2][3], tmp[-2][4])
            # if key == (2, 3):
            #     print(self.port_stats[key])
        now = tmp[-1][0]
        speed = round(self.get_speed(now, pre, period), 1)
        src = key[0]
        for dst in self.topology_monitor.graph[src]:
            if self.topology_monitor.graph[src][dst]['port'][0]==key[1]:
                self.throughputs[src].setdefault(dst, {})
                self.throughputs[src][dst] = speed
                break

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        """
            Save port's stats info
            Calculate port's speed and save it.
        """
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

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        """
            Save port description info.
        """
        msg = ev.msg
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto

        config_dict = {ofproto.OFPPC_PORT_DOWN: "Down",
                       ofproto.OFPPC_NO_RECV: "No Recv",
                       ofproto.OFPPC_NO_FWD: "No Farward",
                       ofproto.OFPPC_NO_PACKET_IN: "No Packet-in"}

        state_dict = {ofproto.OFPPS_LINK_DOWN: "Down",
                      ofproto.OFPPS_BLOCKED: "Blocked",
                      ofproto.OFPPS_LIVE: "Live"}

        for p in ev.msg.body:

            if p.config in config_dict:
                config = config_dict[p.config]
            else:
                config = "up"

            if p.state in state_dict:
                state = state_dict[p.state]
            else:
                state = "up"

            for dst in self.topology_monitor.graph[dpid]:
                if self.topology_monitor.graph[dpid][dst]['port'][0]==p.port_no:
                    self.port_features[dpid].setdefault(dst, {})
                    self.port_features[dpid][dst] = p.curr_speed/1000 #Mbps
                    break


    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        """
            Handle the port status changed event.
        """
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto

        reason_dict = {ofproto.OFPPR_ADD: "added",
                       ofproto.OFPPR_DELETE: "deleted",
                       ofproto.OFPPR_MODIFY: "modified", }
    
    def get_throughput(self):
        return self.throughputs
    
    def get_rm_bw(self):
        return self.rm_bws

    def get_link_utilization(self):
        return self.link_utilizations