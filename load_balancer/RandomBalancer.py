import random

from .AbstractBalancer import AbstracBalancer
from .ServerDiscoverer import ServerNode

class RandomBalancer(AbstracBalancer):

    def __init__(self, liveServers):
         super().__init__(liveServers)

    def pickServer(self, _) -> ServerNode:
        self.updateSnapshot()
        return random.choice(self.getSnapshot())