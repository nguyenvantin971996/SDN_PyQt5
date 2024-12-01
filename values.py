from ryu_controller.setting import MAX_CAPACITY
values_delay = [i*10 for i in range(1,10)]
values_bw = [MAX_CAPACITY]
values_loss = [0]
values_delay_host = [1]
values_bw_host = [1000]
values_cost_host = [1.0]
values_cost = [1.0, 1.1, 1.3, 1.4, 1.7, 2.0, 2.5, 3.3, 5.0, 10.0]


s1 = '''from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
from functools import partial
from mininet.topo import Topo
from mininet.term import makeTerm
from time import sleep

class MyTopo(Topo):
	def build(self, **param):\n'''

s2 = '''
def topology():
	topo = MyTopo()
	link = partial(TCLink)\n'''

s3 = '''\tCLI(net)
	net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	topology()'''