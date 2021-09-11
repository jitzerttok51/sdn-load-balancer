
from .AbstractBalancer import AbstracBalancer

class RoundRobinBalancer(AbstracBalancer):


    def __init__(self, liveServers, config):
        self.liveServers = liveServers
        super().__init__(liveServers, config)

        self.localSnapshot = list(self.getSnapshot())

    def pickServer(self, _):

        self.updateSnapshot()

        if len(self.localSnapshot)>0:
            server = self.localSnapshot.pop(0)
            self.localSnapshot.append(server)
            return server
    
    def updateSnapshot(self):
        updates = super().updateSnapshot()
        added = updates.added
        removed = updates.removed

        # Update snapshot
        for rem in removed:
            self.localSnapshot.remove(rem)
        for add in added:
            self.localSnapshot.append(add)
