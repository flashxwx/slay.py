import sys
from typing import TypedDict

import requests, json

from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class PlayerProfile(TypedDict):
    """ Type of player infomation. """

    id: int
    name: str
    xp: int
    elo: int | float
    clan_tag: str
    kills: int
    deaths: int
    timeOfCreation: int
    timeOfLastLogin: int
    personal_text: str
    ts_nick: int
    name_color_select: int
    isLegacy: int
    hat: int
    killedWithGunCounter: list[int]
    elo2: int | float
    elo3: int | float
    online: bool


def getPlayerProfile(id: int, timeout: int = 10) -> PlayerProfile:
    response = requests.get(
        f"https://54.37.204.175:3000/user/{id}", verify=False, timeout=timeout
    )

    if not response.ok:
        return None
    
    playerInfo = json.loads(response.text)
    playerInfo["killedWithGunCounter"] = json.loads(
        playerInfo["killedWithGunCounter"]
    )

    return playerInfo

def export(definition):
    module = sys.modules[definition.__module__]
    if hasattr(module, "__all__"):
        module.__all__.append(definition.__name__)
    else:
        module.__all__ = [definition.__name__]
    return definition