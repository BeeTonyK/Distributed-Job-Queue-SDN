from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info


class Team3Topo(Topo):

    def build(self):

        s1 = self.addSwitch('s1', protocols='OpenFlow13')

        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s1)
        self.addLink(h4, s1)


def start_network():

    topo = Team3Topo()

    net = Mininet(
        topo=topo,
        controller=None,
        switch=OVSSwitch,
        autoSetMacs=True
    )

    net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6653
    )

    info('\n*** Starting network\n')
    net.start()

    info('\n*** Network started successfully\n')

    CLI(net)

    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    start_network()
