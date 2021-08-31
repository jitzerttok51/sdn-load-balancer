import random

class Random:

    def __init__(self, liveServers):
        self.liveServers = liveServers

    def pickServer(self):
        return random.choice(self.liveServers.getServers())