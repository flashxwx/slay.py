import json, requests

from typing import TypedDict
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from slay.utils import export

__all__ = ["connection", "connections", "socket"]

@export
class PlayerProfile(TypedDict):
    """ Type of player profile. """

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

@export
def get_player_profile(id: int, timeout: int = 10) -> PlayerProfile:
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