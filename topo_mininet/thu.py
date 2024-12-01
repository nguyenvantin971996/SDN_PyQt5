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
		H3 = self.addHost('H3', mac='00:00:00:00:00:03', ip='10.0.0.3')
		H4 = self.addHost('H4', mac='00:00:00:00:00:04', ip='10.0.0.4')
		S1 = self.addSwitch('S1')
		S2 = self.addSwitch('S2')
		S3 = self.addSwitch('S3')
		S4 = self.addSwitch('S4')
		S5 = self.addSwitch('S5')
		self.addLink(H1, S1, 1, 1, bw=1000, delay='1ms', loss=0)
		self.addLink(S1, S2, 2, 1, bw=100, delay='60ms', loss=0)
		self.addLink(S2, S5, 2, 1, bw=100, delay='50ms', loss=0)
		self.addLink(S5, S4, 2, 1, bw=100, delay='70ms', loss=0)
		self.addLink(S4, S1, 2, 3, bw=100, delay='20ms', loss=0)
		self.addLink(S1, S3, 4, 1, bw=100, delay='10ms', loss=0)
		self.addLink(S3, S4, 2, 3, bw=100, delay='80ms', loss=0)
		self.addLink(S3, S5, 3, 3, bw=100, delay='20ms', loss=0)
		self.addLink(S3, S2, 4, 3, bw=100, delay='80ms', loss=0)
		self.addLink(S2, H3, 4, 1, bw=1000, delay='1ms', loss=0)
		self.addLink(S5, H2, 4, 1, bw=1000, delay='1ms', loss=0)
		self.addLink(S4, H4, 4, 1, bw=1000, delay='1ms', loss=0)

def topology():
	topo = MyTopo()
	link = partial(TCLink)
	net = Mininet(topo=topo, controller=RemoteController(name='C1', ip='127.0.0.1', port=6653), link=link)
	net.start()
	sleep(2)
	makeTerm(net['H2'],cmd='bash traffic/H2.sh')
	makeTerm(net['H4'],cmd='bash traffic/H4.sh')
	sleep(2)
	makeTerm(net['H1'],cmd='bash traffic/H1.sh')
	makeTerm(net['H3'],cmd='bash traffic/H3.sh')
	CLI(net)
	net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	topology()