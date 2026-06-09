import json
from typing import NamedTuple, TypedDict, Annotated

from slay.utils import Pipe

RankedSearchCount = int

class AccountLogging(NamedTuple):
    nickname: str
    skin_id: int
    abilities: Annotated["Abilities", json.loads]
    golds: int
    gems: int
    xp: int
    is_mod: int
    is_mod2: int
    is_admin: int
    nickname_color_id: int
    unlocked_skin_ids: str
    clan_tag: str
    clan_role: int
    chests: str
    db_id: int
    unlocked_name_color_ids: str
    unlocked_emotes: Annotated["UnlockedEmotes", json.loads]
    kills_of_weapons: Annotated["KillsOfWeapons", json.loads]
    ranked_search_count: int


class Abilities(TypedDict):
    ...
class UnlockedEmotes(TypedDict):
    ...

class KillsOfWeapons(TypedDict):
    ...