
# Import some POX stuff
from pox.core import core                     # Main POX object
import pox.openflow.libopenflow_01 as of      # OpenFlow 1.0 library
from pox.lib.addresses import IPAddr # Address types
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.arp import arp
from load_balancer.ServerDiscoverer import ServerNode
import time

log = core.getLogger("ServerHealthChecker")

class LiveServerNode(object):
    def __init__(self, node: ServerNode):
        self.expireTime = 0
        self.inTimeout = False
        self.node = node
    
    def __str__(self):
        return str(self.node)

class ServerHealthChecker:

    def __init__(self, servers, serviceIp: IPAddr, endpoints):
        self.servers = [LiveServerNode(server) for server in servers]
        self.serviceIp = serviceIp
        self.endpoints = endpoints

        self.timeout = 60.0
        self.cycleTime = 15.0
    
    def startProbing(self, conn):
        self.probe(conn)

    def nextProbeTime(self):
        return max(0.25, self.cycleTime / float(len(self.servers)))

    def getServers(self):
        return [server.node for server in self.servers ]

    def expire(self):

        t = time.time()

        for server in list(self.servers):
            if server.inTimeout and t > server.expireTime:
                self.log.warn("Server %s down", server.ip)
                self.servers.remove(server)

    def probe(self, conn):

        self.expire()

        server = self.servers.pop(0)
        self.servers.append(server)

        r = arp()
        r.hwtype = r.HW_TYPE_ETHERNET
        r.prototype = r.PROTO_TYPE_IP
        r.opcode = r.REQUEST
        r.hwdst = ETHER_BROADCAST
        r.protodst = server.node.ip
        r.hwsrc = conn.eth_addr
        r.protosrc = self.serviceIp

        e = ethernet(type = ethernet.ARP_TYPE, src=conn.eth_addr, dst=ETHER_BROADCAST)
        e.set_payload(r)

        msg = of.ofp_packet_out()
        msg.data = e.pack()
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
        msg.in_port = of.OFPP_NONE
        conn.send(msg)

        server.inTimeout = True
        server.expireTime = time.time() + self.timeout
        core.call_delayed(self.nextProbeTime(), self.probe, conn)
    
    def match(self, event, conn):
        if event.port in self.endpoints:
            return False

        arpp = event.parsed.find('arp')
        if arpp is None:
            return False

        opcode = arpp.opcode
        srcip  = arpp.protosrc
        return opcode == arpp.REPLY and srcip in self.getServerIps()

    def getServerIps(self):
        return [server.node.ip for server in self.servers]

    def handle(self, event, conn):
        inport = event.port
        arpp = event.parsed.find('arp')
        for server in self.servers:
            if arpp.protosrc == server.node.ip:
                server.inTimeout = False
                log.debug(f"{server} is live")