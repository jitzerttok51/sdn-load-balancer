import random
from .ServerDiscoverer import ServerNode


from .AbstractBalancer import AbstracBalancer
from .LoadDispatcher import LoadDispatcher


class LeastConnectionBalancer(AbstracBalancer):

    def __init__(self, liveServers, config):
         super().__init__(liveServers, config)

    def pickServer(self, ctx: LoadDispatcher) -> ServerNode:
        serverLoad = {}
        
        for server in self.getSnapshot():
            serverLoad[server] = 0

        for _,entry in ctx.flowCache.items():
            if entry.server in serverLoad:
                serverLoad[entry.server] = serverLoad[entry.server] + 1

        choise = min(serverLoad, key=serverLoad.get)
        print(choise)
        return choise
        