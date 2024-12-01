from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
from functools import partial
from mininet.topo import Topo
from mininet.term import makeTerm
from time import sleep

class MyTopo(Topo):
	def build(self, **param):
		H1 = self.addHost('H1', mac='00:00:00:00:00:01', ip='10.0.0.1')
		H2 = self.addHost('H2', mac='00:00:00:00:00:02', ip='10.0.0.2')
		S1 = self.addSwitch('S1')
		S2 = self.addSwitch('S2')
		S3 = self.addSwitch('S3')
		S4 = self.addSwitch('S4')
		S5 = self.addSwitch('S5')
		S6 = self.addSwitch('S6')
		S7 = self.addSwitch('S7')
		S8 = self.addSwitch('S8')
		S9 = self.addSwitch('S9')
		S10 = self.addSwitch('S10')
		S11 = self.addSwitch('S11')
		S12 = self.addSwitch('S12')
		S13 = self.addSwitch('S13')
		S14 = self.addSwitch('S14')
		S15 = self.addSwitch('S15')
		self.addLink(H1, S1, 1, 1, bw=1000, delay='1ms', loss=0)
		self.addLink(H2, S15, 1, 1, bw=1000, delay='1ms', loss=0)
		self.addLink(S1, S2, 2, 1, bw=100, delay='20ms', loss=0)
		self.addLink(S2, S3, 2, 1, bw=100, delay='40ms', loss=0)
		self.addLink(S3, S4, 2, 1, bw=100, delay='90ms', loss=0)
		self.addLink(S1, S5, 3, 1, bw=100, delay='60ms', loss=0)
		self.addLink(S5, S6, 2, 1, bw=100, delay='80ms', loss=0)
		self.addLink(S6, S7, 2, 1, bw=100, delay='90ms', loss=0)
		self.addLink(S7, S15, 2, 2, bw=100, delay='30ms', loss=0)
		self.addLink(S1, S12, 4, 1, bw=100, delay='50ms', loss=0)
		self.addLink(S8, S12, 1, 2, bw=100, delay='20ms', loss=0)
		self.addLink(S12, S10, 3, 1, bw=100, delay='20ms', loss=0)
		self.addLink(S10, S5, 2, 3, bw=100, delay='80ms', loss=0)
		self.addLink(S8, S2, 2, 3, bw=100, delay='80ms', loss=0)
		self.addLink(S11, S13, 1, 1, bw=100, delay='70ms', loss=0)
		self.addLink(S13, S9, 2, 1, bw=100, delay='60ms', loss=0)
		self.addLink(S9, S4, 2, 2, bw=100, delay='20ms', loss=0)
		self.addLink(S9, S14, 3, 1, bw=100, delay='80ms', loss=0)
		self.addLink(S14, S11, 2, 2, bw=100, delay='60ms', loss=0)
		self.addLink(S14, S15, 3, 3, bw=100, delay='10ms', loss=0)
		self.addLink(S15, S4, 4, 3, bw=100, delay='10ms', loss=0)
		self.addLink(S11, S7, 3, 3, bw=100, delay='70ms', loss=0)
		self.addLink(S8, S9, 3, 4, bw=100, delay='80ms', loss=0)
		self.addLink(S10, S11, 3, 4, bw=100, delay='40ms', loss=0)
		self.addLink(S12, S13, 4, 3, bw=100, delay='50ms', loss=0)

def topology():
	topo = MyTopo()
	link = partial(TCLink)
	net = Mininet(topo=topo, controller=RemoteController(name='C1', ip='127.0.0.1', port=6653), link=link)
	net.start()
	sleep(2)
	makeTerm(net['H2'],cmd='bash traffic/H2.sh')
	sleep(2)
	makeTerm(net['H1'],cmd='bash traffic/H1.sh')
	CLI(net)
	net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	topology()