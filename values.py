from ryu_controller.setting import MAX_CAPACITY
valuesDelay = [i*10 for i in range(1,10)]
valuesBw = [MAX_CAPACITY]
valuesLoss = [0]
valuesDelayHost = [1]
valuesBwHost = [1000]
valuesCostHost = [1.0]
valuesCost = [1.0, 1.1, 1.3, 1.4, 1.7, 2.0, 2.5, 3.3, 5.0, 10.0]


s1 = '''from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from functools import partial
from mininet.topo import Topo
from mininet.term import makeTerm
from time import sleep
from threading import Thread

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