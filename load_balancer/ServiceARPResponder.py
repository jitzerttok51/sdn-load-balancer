from pox.core import core                     # Main POX object
import pox.openflow.libopenflow_01 as of      # OpenFlow 1.0 library
import pox.lib.packet as pkt                  # Packet parsing/construction
from pox.lib.addresses import EthAddr, IPAddr, IP_BROADCAST # Address types
import pox.lib.util as poxutil                # Various util functions
import pox.lib.revent as revent               # Event library
import pox.lib.recoco as recoco               # Multitasking library
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.arp import arp

class ServiceARPResponder:

    def __init__(self, serviceIp: IPAddr, endpoints):
        self.serviceIp = serviceIp
        self.endpoints = endpoints
    
    def match(self, event, conn):
        if event.port not in self.endpoints:
            return False

        arpp = event.parsed.find('arp')
        if arpp is None:
            return False

        opcode = arpp.REQUEST
        ip = arpp.protodst
        return arpp and opcode == arpp.REQUEST and ip == self.serviceIp

    def handle(self, event, conn):
        arpp = event.parsed.find('arp')
        askerIP = arpp.protosrc
        askerMAC = arpp.hwsrc

        myMAC = conn.eth_addr
        myIP  = self.serviceIp

        r = arp()
        r.hwtype = r.HW_TYPE_ETHERNET
        r.prototype = r.PROTO_TYPE_IP
        r.opcode = r.REPLY
        r.hwdst = askerMAC
        r.protodst = askerIP
        r.hwsrc = myMAC
        r.protosrc = myIP

        e = ethernet(type = ethernet.ARP_TYPE, src=myMAC, dst=askerMAC)
        e.set_payload(r)

        msg = of.ofp_packet_out()
        msg.data = e.pack()
        msg.actions.append(of.ofp_action_output(port = event.port))
        msg.in_port = of.OFPP_NONE
        conn.send(msg)