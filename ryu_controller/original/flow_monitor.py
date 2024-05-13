from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.ofproto import ofproto_v1_3


from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER

from ryu.lib import hub

from topology_monitor import TopologyMonitor
import setting

class FlowMonitor(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FlowMonitor, self).__init__(*args, **kwargs)

        self.name = 'flow_monitor'

        self.topology_monitor: TopologyMonitor = lookup_service_brick('topology_monitor')
        
        self.monitor = hub.spawn(self._monitor_thread)
        
        self.flow_stats = {} # {dpid: {(in_port, eth_dst, out_port): [(packet_count, byte_count, duration_sec, duration_nsec),... ]},... }
        self.flow_speeds_stats = {} # {dpid: {(in_port, eth_dst, out_port): [(delta_packet, speed),... ]},...  }
        self.flow_speeds = {}

    
    def _monitor_thread(self):
        try:
            while True:
                for dp in self.topology_monitor.datapaths.values():
                    self._request_stats(dp)
                self.get_flow_speeds()
                self.show_flow_monitor()
                hub.sleep(setting.MONITOR_PERIOD)
        except self.topology_monitor is None:
                self.topology_monitor = lookup_service_brick('topology_monitor')
                return
    
    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
    
    def _save_stats(self, _dict, key, value, history_length=2):
        if key not in _dict:
            _dict[key] = []
        _dict[key].append(value)

        if len(_dict[key]) > history_length:
            _dict[key].pop(0)

    def get_speed(self, now, pre, period):
        if period:
            return 8*(now - pre) / (period*10**6)
        else:
            return 0.0

    def _get_time(self, sec, nsec):
        return sec + nsec / (10 ** 9)

    def _get_period(self, n_sec, n_nsec, p_sec, p_nsec):
        return self._get_time(n_sec, n_nsec) - self._get_time(p_sec, p_nsec)
        
    
    def _flow_pair(self, src_key, dst_key, src_port_ltp, dst_port_ltp):
        flow_match = []
        for src in src_key:
            _, src_port, eth_src_src, eth_dst_src = src
            for dst in dst_key:
                dst_port, _, eth_src_dst, eth_dst_dst = dst
                if src_port == src_port_ltp and dst_port == dst_port_ltp and \
                   eth_src_src == eth_src_dst and eth_dst_src == eth_dst_dst:
                    flow_match.append((src, dst))
        return flow_match

    def get_flow_speeds(self):
        try:
            for src in self.topology_monitor.graph:
                self.flow_speeds[src] = {}
                for dst in self.topology_monitor.graph[src]:
                    if src != dst:
                        self.flow_speeds[src][dst] = []
                        src_port, dst_port = self.topology_monitor.graph[src][dst]['port'][0], self.topology_monitor.graph[src][dst]['port'][1]
                        src_key_list = list(self.flow_speeds_stats[src].keys())
                        dst_key_list = list(self.flow_speeds_stats[dst].keys())
                        flow_pairs = self._flow_pair(src_key_list, dst_key_list, src_port, dst_port)
                        for flow in flow_pairs:
                            speed_1 = self.flow_speeds_stats[src][flow[0]]
                            speed_2 = self.flow_speeds_stats[src][flow[1]]
                            self.flow_speeds[src][dst] = [speed_1, speed_2]
        except:
            if self.topology_monitor is None:
                self.topology_monitor = lookup_service_brick('topology_monitor')
            return

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        """
            Save flow stats reply info into self.flow_stats.
            Calculate flow speed and Save it.

            flow_stats: {dpid: { (in_port[(packet_count, byte_count, duration_sec, duration_nsec)]}
            [history][stat_type]
            As: (stat.packet_count, stat.byte_count, stat.duration_sec, stat.duration_nsec)
                        0                 1                 2                 3
        """
        body = ev.msg.body
        dpid = ev.msg.datapath.id

        self.flow_stats.setdefault(dpid, {})

        self.flow_speeds_stats.setdefault(dpid, {})

        # for stat in sorted([flow for flow in body if flow.priority > 0 and flow.priority < 65535],
        #                    key=lambda flow: (flow.match.get('in_port'), flow.match.get('eth_dst'))):
        
        for stat in sorted([flow for flow in body if flow.priority == 32768],
                           key=lambda flow: (flow.match.get('in_port'), flow.match.get('eth_dst'))):

            key = (stat.match['in_port'], stat.instructions[0].actions[0].port,
                   stat.match.get('eth_src'), stat.match.get('eth_dst'))

            value = (stat.packet_count, stat.byte_count,
                     stat.duration_sec, stat.duration_nsec)

            # Monitoring current flow.
            self._save_stats(self.flow_stats[dpid], key, value, 5)
            
            pre = 0
            period = 0
            tmp = self.flow_stats[dpid][key]
            if len(tmp) > 1:
                pre = tmp[-2][1]
                period = self._get_period(tmp[-1][2], tmp[-1][3],
                                          tmp[-2][2], tmp[-2][3])
            now = tmp[-1][1]
            speed = round(self.get_speed(now, pre, period), 2)
            self._save_stats(self.flow_speeds_stats[dpid], key, speed, 100)
    
    def show_flow_monitor(self):
        print(self.flow_speeds)