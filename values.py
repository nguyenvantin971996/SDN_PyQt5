from ryu_controller.setting import MAX_CAPACITY, n_flows
valuesDelay = [i*10 for i in range(1,10)]
valuesBw = [MAX_CAPACITY]
valuesLoss = [0]
valuesDelayHost = [1]
valuesBwHost = [1000]
valuesCostHost = [1.0]
valuesCost = [1.0, 1.1, 1.3, 1.4, 1.7, 2.0, 2.5, 3.3, 5.0, 10.0]
n_links_dynamic = 1
n_steps = 2
durations = [9]


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

s3_dynamic = f'''\tsleep({n_flows+2})
	thread = Thread(target=dynamicChanges, args=(net,))
	thread.start()
	sleep(2)
	CLI(net)
	net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	topology()'''

s_dynamic = f'''
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
	sleep_durations = {durations}
	current_down_links = []
	link_index = 0
	sleep_index = 0
	while True:
		for src, dst in current_down_links:
			net.configLinkStatus(src, dst, 'up')
			info('Link between %s and %s brought UP.\\n'%(src, dst))
		current_down_links = []
		next_links = []
		for i in range({n_links_dynamic}):
			next_link_index = (link_index + i * {n_steps})%len(links_to_toggle)
			next_links.append(links_to_toggle[next_link_index])
		for src, dst in next_links:
			net.configLinkStatus(src, dst, 'down')
			info('Link between %s and %s brought DOWN.\\n'%(src, dst))
			current_down_links.append((src, dst))
		link_index = (link_index + {n_links_dynamic}*{n_steps})%len(links_to_toggle)
		current_sleep = sleep_durations[sleep_index]
		sleep(current_sleep)
		sleep_index = (sleep_index + 1)%len(sleep_durations)
'''