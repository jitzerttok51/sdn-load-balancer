
from .ServerHealthChecker import ServerHealthChecker
from .ServerDiscoverer import ServerNode
from typing import Set, List

class SnapshotUpdate:
    def __init__(self, added: Set[ServerNode], removed: Set[ServerNode]):
        self.added = added
        self.removed = removed

class AbstracBalancer:

    def __init__(self, liveServers: ServerHealthChecker):
        self.liveServers = liveServers

        self.snapshot: Set[ServerNode] = set(self.getLiveServers())

    def getLiveServers(self) -> List[ServerNode]:
        return self.liveServers.getServers()

    def getSnapshot(self) -> Set[ServerNode]:
        return self.snapshot.copy()

    def updateSnapshot(self) -> SnapshotUpdate:
        update: Set[ServerNode] = set(self.getLiveServers())
        added: Set[ServerNode] = update.difference(self.snapshot)
        removed: Set[ServerNode] = self.snapshot.difference(update)
        self.snapshot = update
        return SnapshotUpdate(added, removed)