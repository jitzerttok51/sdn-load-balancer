from pox.core import core                     # Main POX object
import pox.openflow.libopenflow_01 as of      # OpenFlow 1.0 library
import pox.lib.packet as pkt                  # Packet parsing/construction
from pox.lib.addresses import EthAddr, IPAddr, IP_BROADCAST # Address types
import pox.lib.util as poxutil                # Various util functions
import pox.lib.revent as revent               # Event library
import pox.lib.recoco as recoco               # Multitasking library
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.arp import arp

import time
import random

from load_balancer.ServerDiscoverer import ServerNode

FLOW_CACHE_TIMEOUT = 5 * 60 # seconds
FLOW_TIMEOUT = 10 # seconds

log = core.getLogger("LoadDispatcher")

class FlowEntry:
    def __init__(self, server: ServerNode, servicePort: int, clientIp: IPAddr, clientPort: int, switchPort: int):
        self.server = server
        self.servicePort = servicePort
        self.clientIp = clientIp
        self.clientPort = clientPort
        self.switchPort = switchPort
        self.refresh()
    
    def refresh (self):
        self.timeout = time.time() + FLOW_CACHE_TIMEOUT

    @property
    def isExpired (self):
        return time.time() > self.timeout

class LoadDispatcher:

    def __init__(self, liveServers, serviceIp):
        self.liveServers = liveServers
        self.serviceIp = serviceIp

        self.flowCache = {}
        self.clientMacs = {}
    
    def getServers(self):
        return self.liveServers.getServers()
    
    def getServerIps(self):
        return [server.ip for server in self.getServers()]

    def cleanCache(self):
        for socket, flow in self.flowCache.items():
            if flow.isExpired:
                del self.flowCache[socket]

    def match(self, event, conn):
        self.cleanCache()

        #Match server -> client ARP resolution
        arpPacket = event.parsed.find('arp')
        if arpPacket is not None:
            return arpPacket.protosrc in self.getServerIps() and arpPacket.protodst in self.clientMacs

        tcpPacket = event.parsed.find('tcp')
        return tcpPacket is not None

    def pickServer(self):
        return random.choice(self.getServers())

    def handle(self, event, conn):
        packet = event.parsed

        arpPacket = event.parsed.find('arp')

        if arpPacket is not None:
            r = arp()
            r.hwtype = r.HW_TYPE_ETHERNET
            r.prototype = r.PROTO_TYPE_IP
            r.opcode = r.REPLY
            r.hwdst = arpPacket.hwsrc
            r.protodst = arpPacket.protosrc
            r.hwsrc = self.clientMacs [arpPacket.protodst]
            r.protosrc = arpPacket.protodst

            e = ethernet(type = ethernet.ARP_TYPE, src=conn.eth_addr, dst=arpPacket.hwsrc)
            e.set_payload(r)

            msg = of.ofp_packet_out()
            msg.data = e.pack()
            msg.actions.append(of.ofp_action_output(port = event.port))
            msg.in_port = of.OFPP_NONE
            conn.send(msg)
            return None

        tcpPacket = packet.find('tcp')
        ipPacket = packet.find('ipv4')

        # log.debug(f"Handle: {ipPacket.srcip}:{tcpPacket.srcport} -> {ipPacket.dstip}:{tcpPacket.dstport}")

        if ipPacket.dstip == self.serviceIp:
            # Inbound

            self.clientMacs[ipPacket.srcip] = packet.src

            socket = ipPacket.srcip,tcpPacket.srcport,self.serviceIp,tcpPacket.dstport

            flow = None
            if socket in self.flowCache:
                flow = self.flowCache[socket]

            if flow is None or flow.server.ip not in self.getServerIps():
                if len(self.getServerIps()) == 0:
                    log.warn("No servers to handle request")
                    return True
                
                server = self.pickServer()
                log.debug(f"Redirecting {ipPacket.srcip}:{tcpPacket.srcport} to {server}")
                flow = FlowEntry(server, tcpPacket.dstport, ipPacket.srcip, tcpPacket.srcport, event.port)
                self.flowCache[socket] = flow
            else:
                flow.refresh()

            actions = [
                of.ofp_action_dl_addr.set_dst(flow.server.mac),
                of.ofp_action_nw_addr.set_dst(flow.server.ip),
                of.ofp_action_output(port = flow.server.port)
            ]

            match = of.ofp_match.from_packet(packet, event.port)

            msg = of.ofp_flow_mod(command=of.OFPFC_ADD,
                    idle_timeout=FLOW_TIMEOUT,
                    hard_timeout=of.OFP_FLOW_PERMANENT,
                    data=event.ofp,
                    actions=actions,
                    match=match)
            conn.send(msg)
        elif ipPacket.srcip in self.getServerIps():
            # Outbound

            socket = ipPacket.dstip,tcpPacket.dstport,self.serviceIp,tcpPacket.srcport
            
            if socket not in self.flowCache:
                log.debug(f"No client for {socket}")
                return True
            
            flow = self.flowCache[socket]
            flow.refresh()

            actions = [
                of.ofp_action_dl_addr.set_src(conn.eth_addr),
                of.ofp_action_nw_addr.set_src(self.serviceIp),e
                of.ofp_action_output(port = flow.switchPort)
            ]

            match = of.ofp_match.from_packet(packet, event.port)

            msg = of.ofp_flow_mod(command=of.OFPFC_ADD,
                    idle_timeout=FLOW_TIMEOUT,
                    hard_timeout=of.OFP_FLOW_PERMANENT,
                    data=event.ofp,
                    actions=actions,
                    match=match)
            conn.send(msg)
        else:
            # continue to drop that packet
            return True