
from .AbstractBalancer import AbstracBalancer
from pox.lib.addresses import IPAddr 
from .ServerDiscoverer import ServerNode


from .AbstractBalancer import AbstracBalancer
from .LoadDispatcher import LoadDispatcher

class WeightedRoundRobinBalancer(AbstracBalancer):

    def __init__(self, liveServers, config):
        self.liveServers = liveServers
        super().__init__(self.liveServers, config)

        self.weights = {}
        for entry in self.config.methodArgs["weights"]:
            self.weights[IPAddr(entry["server"])] = entry["weight"]
        

        self.localSnapshot = list(self.getSnapshot())
        self.applyWeights()

    def pickServer(self, ctx: LoadDispatcher) -> ServerNode:

        self.updateSnapshot()

        serverLoad = {}

        for _,entry in ctx.flowCache.items():
            if entry.server not in serverLoad:
                serverLoad[entry.server] = 0
            serverLoad[entry.server] = serverLoad[entry.server] + 1

        print(serverLoad)

        if len(self.localSnapshot)>0:
            server = self.weightedSnapshot.pop(0)
            self.weightedSnapshot.append(server)
            return server
    
    def updateSnapshot(self):
        updates = super().updateSnapshot()
        added = updates.added
        removed = updates.removed

        if len(added) != 0 or len(removed) != 0:
            # Update snapshot
            for rem in removed:
                self.localSnapshot.remove(rem)
            for add in added:
                self.localSnapshot.append(add)
            self.applyWeights()

    def applyWeights(self):
        self.weightedSnapshot = []

        for n in self.localSnapshot:
            count = 1
            if n.ip in self.weights:
                count = self.weights[n.ip]
            for _ in range(count):
                self.weightedSnapshot.append(n)