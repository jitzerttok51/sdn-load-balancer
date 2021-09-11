"""Custom topology example

Two directly connected switches plus a host for each switch:

   host --- switch --- switch --- host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.node import RemoteController

import os
import os.path as path

REMOTE_CONTROLLER_IP="192.168.56.1"
REMOTE_CONTROLLER_PORT=6634

def ensureList(obj):
    if type(obj) is not list:
        return [obj]
    return obj

class MyTopo( Topo ):
    "Simple topology example."

    def build( self ):
        loadBalancer = self.addSwitch( 's1' )
        network = self.addSwitch( 's2' )

        self.addLink(loadBalancer, network, port1=1, port2=1)

        nServers=4
        nClients=10

        self.serverNodes = []

        for i in range(1, nServers+1):
            name = 'h'+str(i)
            server = self.addHost(name)
            self.addLink(loadBalancer, server, port1=i+1)
            self.serverNodes.append(name)

        self.clientNodes = []
        for i in range(1, nClients+1):
            name = 'h'+str(nServers+i)
            client = self.addHost(name)
            self.addLink(network, client)
            self.clientNodes.append(name)
            # self.addLink(loadBalancer, client, port1=1)

if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')

    topo = MyTopo()

    net = Mininet(topo=topo, controller=None)
    net.addController("c0",
                      controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP,
                      port=REMOTE_CONTROLLER_PORT)
    net.start()
    print "Starting http servers"

    workdir = path.abspath(path.join(path.dirname(path.realpath(__file__)), os.pardir, 'test_balancer'))
    

    servers = ensureList(net.get(*topo.serverNodes))
    for server in servers:
        server.cmd("cd " + workdir )
        server.cmd("bash run.sh " + server.name )
        # server.cmd('eval "python -m SimpleHTTPServer &"')

    clients = ensureList(net.get(*ensureList(topo.clientNodes)))

    nRequests = 100

    command = "curl 10.1.1.1:5000"
    for i in range(nRequests):
        print i
        for client in clients:
            print client.name + ": " + command
            client.cmd(command)
  
    statistics = {}
    for server in servers:
        f = None
        try:
            f = open(server.name + '.txt')
            statistics[server.name] = int(f.read())
        finally:
            if f is not None:
                f.close()
    
    print "Stats: " + str(statistics)
    # CLI(net)
    net.stop()

topos = { 'mytopo': ( lambda: MyTopo() ) }
