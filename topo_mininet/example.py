from mininet.net import Mininet
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
		self.addLink(H1, S1, 1, 1, bw=1000, delay='1ms', loss=0)
		self.addLink(S1, S2, 2, 1, bw=100, delay='90ms', loss=0)
		self.addLink(S2, S3, 2, 1, bw=100, delay='10ms', loss=0)
		self.addLink(S3, S7, 2, 1, bw=100, delay='80ms', loss=0)
		self.addLink(S7, S5, 2, 1, bw=100, delay='10ms', loss=0)
		self.addLink(S5, S4, 2, 1, bw=100, delay='90ms', loss=0)
		self.addLink(S4, S1, 2, 3, bw=100, delay='90ms', loss=0)
		self.addLink(S2, S6, 3, 1, bw=100, delay='60ms', loss=0)
		self.addLink(S6, S4, 2, 3, bw=100, delay='40ms', loss=0)
		self.addLink(S6, S5, 3, 3, bw=100, delay='60ms', loss=0)
		self.addLink(S6, S3, 4, 3, bw=100, delay='50ms', loss=0)
		self.addLink(S7, H2, 3, 1, bw=1000, delay='1ms', loss=0)

def topology():
	topo = MyTopo()
	link = partial(TCLink)
	net = Mininet(topo=topo, controller=RemoteController(name='C1', ip='127.0.0.1', port=6653), link=link)
	net.start()
	sleep(2)
	makeTerm(net['H1'],cmd='bash traffic/H1.sh')
	makeTerm(net['H2'],cmd='bash traffic/H2.sh')
	sleep(2)
	CLI(net)
	net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	topology()

