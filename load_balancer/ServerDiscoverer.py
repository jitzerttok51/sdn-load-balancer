
from pox.core import core                     
import pox.openflow.libopenflow_01 as of      
from pox.lib.addresses import EthAddr, IPAddr 
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.arp import arp

log = core.getLogger("ServerDiscoverer")
DISCOVER_TIME = 3

class ServerNode:

    def __init__(self, ip: IPAddr, mac: EthAddr, port: int):
        self.ip = ip
        self.mac = mac
        self.port = port

    def __str__(self):
        return f"Server({self.ip},{self.mac},{self.port})"

    def __repr__(self) -> str:
        return str(self)

class ServerDiscoverer(object):
    
    def __init__(self, endpoints, serviceIp: IPAddr):
        self.endpoints = endpoints
        self.serviceIp = serviceIp
        self.running = False
        self.servers = []
    
    def discover(self, conn, afterDiscover):
        self.servers = []
        self.running = True

        for i in range(1, 255):
            ip = IPAddr(f"10.0.0.{i}")
            self.pingIP(ip, conn)

        def stop():
            self.running = False
            afterDiscover(self.servers)
            self.servers = []
        core.call_delayed(DISCOVER_TIME, stop)
    
    def pingIP(self, ip, conn):
        log.debug(f"Pinging {ip}")
        r = arp()
        r.hwtype = r.HW_TYPE_ETHERNET
        r.prototype = r.PROTO_TYPE_IP
        r.opcode = r.REQUEST
        r.hwdst = ETHER_BROADCAST
        r.protodst = ip
        r.hwsrc = conn.eth_addr
        r.protosrc = self.serviceIp

        e = ethernet(type = ethernet.ARP_TYPE, src=conn.eth_addr, dst=ETHER_BROADCAST)
        e.set_payload(r)

        msg = of.ofp_packet_out()
        msg.data = e.pack()
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
        msg.in_port = of.OFPP_NONE
        conn.send(msg)


    def match(self, event, conn):
        if not self.running:
            return False
        if event.port in self.endpoints:
            return False
        arpp = event.parsed.find('arp')
        return arpp and arpp.opcode == arpp.REPLY

    def handle(self, event, conn):
        arpp = event.parsed.find('arp')
        server = ServerNode(arpp.protosrc, arpp.hwsrc, event.port)
        log.debug(f"Found server node {str(server)}")
        self.servers.append(server)

