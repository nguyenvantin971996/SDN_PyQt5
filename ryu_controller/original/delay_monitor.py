from __future__ import division
from ryu import cfg
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.topology.switches import Switches
from ryu.topology.switches import LLDPPacket
from collections import defaultdict
import networkx as nx
import json
import time
import setting
import copy
from topology_monitor import TopologyMonitor

CONF = cfg.CONF

class DelayMonitor(app_manager.RyuApp):
    """
        DelayMonitor is a Ryu app for collecting link delay.
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DelayMonitor, self).__init__(*args, **kwargs)
        self.name = 'delay_monitor'
        self.sending_echo_request_interval = 0.05
        self.sw_module: Switches = lookup_service_brick('switches')
        self.topology_monitor: TopologyMonitor = lookup_service_brick('topology_monitor')
        self.echo_latency = {}
        self.latencies = {}
        self.normalized_latencies = {}
        self.measure_thread = hub.spawn(self._detector)

    def _detector(self):
        """
            Delay detecting functon.
            Send echo request and calculate link delay periodically
        """
        while CONF.delay == 1:
            self._send_echo_request()
            self.create_link_latency()
            self.get_latency_vs_normalized()
            hub.sleep(setting.DELAY_DETECTING_PERIOD)

    def _send_echo_request(self):
        """
            Seng echo request msg to datapath.
        """
        if self.topology_monitor is not None:
            try:
                for datapath in list(self.topology_monitor.datapaths.values()):
                    parser = datapath.ofproto_parser

                    data_time = "%.12f" % time.time()
                    byte_arr = bytearray(data_time.encode())

                    echo_req = parser.OFPEchoRequest(datapath,
                                                        data=byte_arr)
                    datapath.send_msg(echo_req)

                    hub.sleep(self.sending_echo_request_interval)
            except Exception as e:
                self.logger.error("Error sending echo request: %s", e)

        else:
            self.topology_monitor = lookup_service_brick('topology_monitor')
            return


    @set_ev_cls(ofp_event.EventOFPEchoReply, MAIN_DISPATCHER)
    def echo_reply_handler(self, ev):
        """
            Handle the echo reply msg, and get the latency of link.
        """
        now_timestamp = time.time()
        try:
            latency = now_timestamp - eval(ev.msg.data)
            self.echo_latency[ev.msg.datapath.id] = latency
        except:
            return

    def calculate_latency(self, src, dst):
        """
            Get link delay.
                        Controller
                        |        |
        src echo latency|        |dst echo latency
                        |        |
                   SwitchA-------SwitchB
                        
                    fwd_delay--->
                        <----reply_delay
            delay = (forward delay + reply delay - src datapath's echo latency
        """
        try:
            fwd_delay = self.topology_monitor.graph[src][dst]['lldpdelay']
            re_delay = self.topology_monitor.graph[dst][src]['lldpdelay']
            src_latency = self.echo_latency[src]
            dst_latency = self.echo_latency[dst]
            
            latency = round((fwd_delay + re_delay - src_latency - dst_latency)*1000/2)
            return max(latency, 0)
        except:
            return float('inf')

    def _save_lldp_delay(self, src=0, dst=0, lldpdelay=0):
        try:
            self.topology_monitor.graph[src][dst]['lldpdelay'] = lldpdelay
        except:
            if self.topology_monitor is None:
                self.topology_monitor = lookup_service_brick('network_awareness')
            return

    def create_link_latency(self):
        """
            Create link delay data, and save it into graph object.
        """
        try:
            for src in self.topology_monitor.graph:
                for dst in self.topology_monitor.graph[src]:
                    if src == dst:
                        continue
                    latency = self.calculate_latency(src, dst)
                    if latency == float('inf'):
                        latency = None
                    self.topology_monitor.graph[src][dst]['latency'] = latency
        except:
            if self.topology_monitor is None:
                self.topology_monitor = lookup_service_brick('topology_monitor')
            return

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
            Parsing LLDP packet and get the delay of link.
        """
        msg = ev.msg
        try:
            src_dpid, src_port_no = LLDPPacket.lldp_parse(msg.data)
            dpid = msg.datapath.id
            if self.sw_module is None:
                self.sw_module = lookup_service_brick('switches')

            for port in self.sw_module.ports.keys():
                if src_dpid == port.dpid and src_port_no == port.port_no:
                    delay = self.sw_module.ports[port].delay
                    self._save_lldp_delay(src=src_dpid, dst=dpid,
                                          lldpdelay=delay)
        except LLDPPacket.LLDPUnknownFormat as e:
            return
    
    def get_latency_vs_normalized(self):
        try:
            max_delay = setting.MAX_DELAY
            for src in self.topology_monitor.graph:
                self.latencies.setdefault(src, {})
                self.normalized_latencies.setdefault(src, {})
                for dst in self.topology_monitor.graph[src]:
                    if 'latency' in self.topology_monitor.graph[src][dst].keys():
                        self.latencies[src][dst] = self.topology_monitor.graph[src][dst]['latency']
                        if self.topology_monitor.graph[src][dst]['latency'] <= max_delay:
                            self.normalized_latencies[src][dst] = round(self.topology_monitor.graph[src][dst]['latency']/max_delay,1)
                        else:
                            self.normalized_latencies[src][dst] = 1.0
        except:
            print("Wait...")
    
    def get_latency(self):
        return self.latencies
    
    def get_normalized_latency(self):
        return self.normalized_latencies