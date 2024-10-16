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
		H3 = self.addHost('H3', mac='00:00:00:00:00:03', ip='10.0.0.3')
		H4 = self.addHost('H4', mac='00:00:00:00:00:04', ip='10.0.0.4')
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
		self.addLink(S1, S2, 1, 1, bw=100, delay='30ms', loss=0)
		self.addLink(S2, S3, 2, 1, bw=100, delay='90ms', loss=0)
		self.addLink(S3, S4, 2, 1, bw=100, delay='10ms', loss=0)
		self.addLink(S4, S12, 2, 1, bw=100, delay='30ms', loss=0)
		self.addLink(S12, S7, 2, 1, bw=100, delay='70ms', loss=0)
		self.addLink(S7, S6, 2, 1, bw=100, delay='70ms', loss=0)
		self.addLink(S6, S5, 2, 1, bw=100, delay='30ms', loss=0)
		self.addLink(S5, S1, 2, 2, bw=100, delay='40ms', loss=0)
		self.addLink(S1, S9, 3, 1, bw=100, delay='20ms', loss=0)
		self.addLink(S1, S8, 4, 1, bw=100, delay='50ms', loss=0)
		self.addLink(S10, S12, 1, 3, bw=100, delay='50ms', loss=0)
		self.addLink(S12, S11, 4, 1, bw=100, delay='90ms', loss=0)
		self.addLink(S2, S8, 3, 2, bw=100, delay='40ms', loss=0)
		self.addLink(S4, S10, 3, 2, bw=100, delay='40ms', loss=0)
		self.addLink(S7, S11, 3, 2, bw=100, delay='50ms', loss=0)
		self.addLink(S5, S9, 3, 2, bw=100, delay='90ms', loss=0)
		self.addLink(S8, S9, 3, 3, bw=100, delay='70ms', loss=0)
		self.addLink(S10, S11, 3, 3, bw=100, delay='20ms', loss=0)
		self.addLink(S3, S10, 3, 4, bw=100, delay='30ms', loss=0)
		self.addLink(S9, S6, 4, 3, bw=100, delay='40ms', loss=0)
		self.addLink(S8, S10, 4, 5, bw=100, delay='60ms', loss=0)
		self.addLink(S9, S11, 5, 4, bw=100, delay='60ms', loss=0)
		self.addLink(H1, S1, 1, 5, bw=1000, delay='1ms', loss=0)
		self.addLink(H3, S2, 1, 4, bw=1000, delay='1ms', loss=0)
		self.addLink(S12, H2, 5, 1, bw=1000, delay='1ms', loss=0)
		self.addLink(S7, H4, 4, 1, bw=1000, delay='1ms', loss=0)
		self.addLink(S2, S10, 5, 6, bw=100, delay='40ms', loss=0)
		self.addLink(S7, S9, 5, 6, bw=100, delay='40ms', loss=0)

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
	sleep_durations = [9]
	current_down_links = []
	link_index = 0
	sleep_index = 0
	while True:
		for src, dst in current_down_links:
			net.configLinkStatus(src, dst, 'up')
			info('Link between %s and %s brought UP.\n'%(src, dst))
		current_down_links = []
		next_links = []
		for i in range(1):
			next_link_index = (link_index + i * 2)%len(links_to_toggle)
			next_links.append(links_to_toggle[next_link_index])
		for src, dst in next_links:
			net.configLinkStatus(src, dst, 'down')
			info('Link between %s and %s brought DOWN.\n'%(src, dst))
			current_down_links.append((src, dst))
		link_index = (link_index + 1*2)%len(links_to_toggle)
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
	makeTerm(net['H4'],cmd='bash traffic/H4.sh')
	sleep(2)
	makeTerm(net['H1'],cmd='bash traffic/H1.sh')
	makeTerm(net['H3'],cmd='bash traffic/H3.sh')
	sleep(6)
	thread = Thread(target=dynamicChanges, args=(net,))
	thread.start()
	sleep(2)
	CLI(net)
	net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	topology()