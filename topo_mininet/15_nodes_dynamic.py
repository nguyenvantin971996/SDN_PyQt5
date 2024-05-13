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

def extractSwitchLinks(topo):
	links = topo.links(withInfo=True)
	switch_links = []
	for link in links:
		node1, node2, info = link
		if node1.startswith('S') and node2.startswith('S'):
			switch_links.append((node1, node2))
	return switch_links

def dynamicChanges(net):
	links_to_toggle = extractSwitchLinks(net.topo)
	sleep_durations = [3, 3, 2, 3, 3]
	current_down_links = []
	link_index = 0
	sleep_index = 0
	while True:
		for src, dst in current_down_links:
			net.configLinkStatus(src, dst, 'up')
			#info('Link between %s and %s brought UP.\n'%(src, dst))
		current_down_links = []
		next_links = links_to_toggle[link_index:link_index+3]
		if len(next_links) < 3:
			next_links += links_to_toggle[:3 - len(next_links)]
		for src, dst in next_links:
			net.configLinkStatus(src, dst, 'down')
			#info('Link between %s and %s brought DOWN.\n'%(src, dst))
			current_down_links.append((src, dst))
		link_index = (link_index + 3)%len(links_to_toggle)
		current_sleep = sleep_durations[sleep_index]
		sleep(current_sleep)
		sleep_index = (sleep_index + 1)%len(sleep_durations)

def topology():
	topo = MyTopo()
	link = partial(TCLink)
	net = Mininet(topo=topo, controller=RemoteController(name='C1', ip='127.0.0.1', port=6653), link=link)
	net.start()
	sleep(2)
	makeTerm(net['H2'],cmd='bash traffic/H2.sh')
	sleep(2)
	makeTerm(net['H1'],cmd='bash traffic/H1.sh')
	sleep(10)
	thread = Thread(target=dynamicChanges, args=(net,))
	thread.start()
	sleep(2)
	CLI(net)
	net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	topology()