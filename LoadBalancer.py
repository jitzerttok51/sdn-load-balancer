from pox.core import core                     
import pox.openflow.libopenflow_01 as of      
              
from pox.lib.addresses import IPAddr 
import pox.lib.util as poxutil
import pox.lib.revent as revent
import json
from pox.lib.util import dpid_to_str

from load_balancer.ServiceARPResponder import ServiceARPResponder
from load_balancer.ServerDiscoverer import ServerDiscoverer
from load_balancer.ServerHealthChecker import ServerHealthChecker
from load_balancer.LoadDispatcher import LoadDispatcher

import importlib

# Create a logger for this component
log = core.getLogger("LoadBalancer")

class ConfigStore:

    def __init__(self, filename: str):
        with open(filename, 'r') as stream:
            data = json.load(stream)
            self.serviceIp = data["service"]
            endp = data["endpoints"]
            if type(endp) is not list:
                endp = [endp]
            
            for ep in endp:
                if type(ep) is not int:
                    raise ValueError("All endpoint parameters must be of type 'int'")
            self.endpoints = endp

            id = data["dpid"]
            if type(id) is not int:
                 raise ValueError("The dpod parameters must be of type 'int'")
            self.dpid = id

            mth = data["method"]
            if type(mth) is str:
                self.method = mth
                self.methodArgs = {}
            else:
                self.methodArgs = mth
                self.method = mth["name"]

class DropHandler:
    def match(self, event, conn):
        return True
    
    def handle(self, event, conn):
        if event.ofp.buffer_id is not None:
            msg = of.ofp_packet_out(data = event.ofp)
            conn.send(msg)

class LoadBalancer (object):

    def __init__(self, conn, config: ConfigStore):
        self.connection = conn
        self.connection.addListeners(self)
        self.endpoints = config.endpoints
        self.serviceIp = IPAddr(config.serviceIp)

        discoverer = ServerDiscoverer(config.endpoints, self.serviceIp)
        log.info(discoverer.__module__)

        self.handlers = [
            ServiceARPResponder(self.serviceIp, self.endpoints),
            discoverer
        ]

        def after(servers):
            self.handlers.remove(discoverer)
            
            healthChecker = ServerHealthChecker(servers, self.serviceIp, self.endpoints)

            module = importlib.import_module("load_balancer."+config.method)
            class_ = getattr(module, config.method)
            instance = class_(healthChecker, config)


            dispatcher = LoadDispatcher(healthChecker, self.serviceIp, instance)

            self.handlers.append(healthChecker)
            self.handlers.append(dispatcher)

            healthChecker.startProbing(self.connection)
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
def launch (config):
  """
  The default launcher just logs its arguments
  """

  config = ConfigStore(config)

  if config.dpid is not None:
    global _dpid
    _dpid = config.dpid

  def handleConn(event: revent.Event):
    global _dpid

    if _dpid is None:
        _dpid = event.dpid
    
    if event.dpid != _dpid:
        log.info(f"Ignoring Switch: {eventDpidToStr(event)}")
        return
    
    if not core.hasComponent("test_balancer"):
        core.registerNew(LoadBalancer, event.connection, config)
        log.info(f"Started load balancer on switch: {eventDpidToStr(event)}")

  core.openflow.addListenerByName("ConnectionUp", handleConn)

  def eventDpidToStr(event):
      return f"{dpid_to_str(event.dpid)} ({event.dpid})"