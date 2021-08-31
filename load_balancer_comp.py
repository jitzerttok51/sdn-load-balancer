"""
A skeleton POX component

You can customize this to do whatever you like.  Don't forget to
adjust the Copyright above, and to delete the Apache license if you
don't want to release under Apache (but consider doing so!).

Rename this file to whatever you like, .e.g., mycomponent.py.  You can
then invoke it with "./pox.py mycomponent" if you leave it in the
ext/ directory.

Implement a launch() function (as shown below) which accepts commandline
arguments and starts off your component (e.g., by listening to events).

Edit this docstring and your launch function's docstring.  These will
show up when used with the help component ("./pox.py help --mycomponent").
"""

# Import some POX stuff
from pox.core import core                     # Main POX object
import pox.openflow.libopenflow_01 as of      # OpenFlow 1.0 library
import pox.lib.packet as pkt                  # Packet parsing/construction
from pox.lib.addresses import EthAddr, IPAddr # Address types
import pox.lib.util as poxutil                # Various util functions
import pox.lib.revent as revent               # Event library
import pox.lib.recoco as recoco               # Multitasking library
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.arp import arp
import time
from pox.lib.util import dpid_to_str, str_to_dpid

from load_balancer.ServiceARPResponder import ServiceARPResponder
from load_balancer.ServerDiscoverer import ServerDiscoverer, ServerNode
from load_balancer.ServerHealthChecker import ServerHealthChecker
from load_balancer.LoadDispatcher import LoadDispatcher
from load_balancer.Random import Random

# Create a logger for this component
log = core.getLogger("test_balancer")

class DropHandler:
    def match(self, event, conn):
        return True
    
    def handle(self, event, conn):
        if event.ofp.buffer_id is not None:
            msg = of.ofp_packet_out(data = event.ofp)
            conn.send(msg)

class test_balancher (object):

    def __init__(self, conn, serviceIp, endpoints):
        self.connection = conn
        self.connection.addListeners(self)
        self.endpoints = endpoints
        self.serviceIp = IPAddr(serviceIp)

        discoverer = ServerDiscoverer(endpoints, self.serviceIp)

        self.handlers = [
            ServiceARPResponder(self.serviceIp, self.endpoints),
            discoverer
        ]

        def after(servers):
            self.handlers.remove(discoverer)
            
            healthChecker = ServerHealthChecker(servers, self.serviceIp, self.endpoints)
            dispatcher = LoadDispatcher(healthChecker, self.serviceIp, Random(healthChecker))

            self.handlers.append(healthChecker)
            self.handlers.append(dispatcher)

            # healthChecker.startProbing(self.connection)
        discoverer.discover(self.connection, after)
    
    def _handle_PacketIn (self, event):
        for handler in self.handlers + [DropHandler()]:
            if handler.match(event, self.connection):
                result = handler.handle(event, self.connection)
                if result is None:
                    break

    def floodAllPorts(self, event):
        msg = of.ofp_packet_out(data = event.ofp)
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
        msg.in_port = event.port
        self.connection.send(msg)
        return None
        
_dpid = None

@poxutil.eval_args
def launch (serviceIp, endpoints, dpid = None):
  """
  The default launcher just logs its arguments
  """

  if dpid is not None:
    global _dpid
    try:
        _dpid = int(dpid)
    except ValueError:
        raise ValueError("--dpid argument should be an int")

  if type(endpoints) is tuple:
    for endpoint in endpoints:
      if type(endpoint) is not int:
          raise ValueError("--endpoints argument should be ints")
  elif type(endpoints) is not int:
          raise ValueError("--endpoints argument should be ints")
  else:
      endpoints = [endpoints]

  def handleConn(event):
    global _dpid

    if _dpid is None:
        _dpid = event.dpid
    
    if event.dpid != _dpid:
        log.info(f"Ignoring Switch: {eventDpidToStr(event)}")
        return
    
    if not core.hasComponent("test_balancer"):
        core.registerNew(test_balancher, event.connection, serviceIp, endpoints)
        log.info(f"Started load balancer on switch: {eventDpidToStr(event)}")

  core.openflow.addListenerByName("ConnectionUp", handleConn)

  def eventDpidToStr(event):
      return f"{dpid_to_str(event.dpid)} ({event.dpid})"