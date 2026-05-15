from enum import Enum

from slay.utils import export

@export
class Socket(Enum):
    SOCIAL = ("eu.slay.one", "54.37.204.175", 62202, 1)
    EU = ("eu.slay.one", "54.37.204.175", 62203, 0)
    AM = ("na.slay.one", "51.79.86.227", 62203, 0)
    ASIA = ("asia.slay.one", "51.79.251.73", 62203, 0)

    @property
    def domain_name(self) -> str:
        return self.value[0]

    @property
    def ip_addr(self) -> str:
        return self.value[1]

    @property
    def port(self) -> str:
        return self.value[2]
    
    @property
    def type(self) -> str:
        value = self.value[3]

        if value == 0: return "Game Server Socket"
        elif value == 1: return "Social Server Socket"

    def __str__(self) -> str:
        return self.name