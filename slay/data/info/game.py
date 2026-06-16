from typing import NamedTuple, Annotated
from enum import Enum

from slay.data.info.decorate import NicknameColor
from slay.utils import Pipe

ConnectionId = int
InGameId = int

def PlayerId(string: str):
    try:
        return int(string)
    except:
        return -1

class GameMode(Enum):
    TEAM_DEATHMATCH = 1
    CAPTURE_THE_FLAG = 2
    DEATHMATCH = 4
    INFECTION = 5

    @property
    def id(self) -> int:
        return self.value

class GameProfile(NamedTuple):
    id: int
    map_name: str
    player_amount: int
    max_player_amount: int
    mode: Annotated[GameMode, Pipe(int, GameMode)]
    map_height: int
    map_witdh: int
    tag: str
    map_thumbnail_data: str

class Game(NamedTuple):
    map_data: str
    mode: Annotated[GameMode, Pipe(int, GameMode)]
    max_round_ticks: int
    current_tick: int
    team_1_scores: int
    team_2_scores: int
    red_flag_x: float
    red_flag_y: float
    blue_flag_x: float
    blue_flag_y: float
    max_round_ticks: int
    """ To ensure compatibility with the old replay version (<=1) """
    current_tick: int
    """ To ensure compatibility with the old replay version (<=1) """
    game_id: int
    """ To ensure compatibility with the old replay version (<=1) """

class Player(NamedTuple):
    in_game_id: int
    x: int
    y: int
    nickname: str
    hp: float
    armor: float
    kills: int
    deaths: int
    weapon_id: int
    moving_to_x: int
    moving_to_y: int
    skin_id: int
    team_id: int
    is_invisible: int
    max_hp: float
    hp_regeneration_rate: float
    clan_tag: str
    authentication_level: int
    souls: float
    mp_regeneration_rate: float
    invisible_costing_rate: float
    score: float
    is_zombie: int
    is_fake_corpse: int
    is_zombie_boss: int
    id: PlayerId
    db_id: int
    nickname_color: Annotated[NicknameColor, Pipe(int, NicknameColor)]

class SummonedZombie(NamedTuple):
    in_game_id: int
    x: float
    y: float
    hp: float
    moving_to_x: float
    moving_to_y: float
    max_hp: float
    hp_regeneration_rate: float
    randomizer: float
    image_scale: float
    name: str

class UsedAmmoRespawn(NamedTuple):
    in_game_id: int
    ticks_left_to_respawn: int
    """ Have to minus 2 to get the actual ticks left to respawn """

class ObjectDetail(NamedTuple):
    ticks_left_to_live: int
    weapon_id: int = -1

class Object(NamedTuple):
    in_game_id: int
    x: float
    y: float
    ability_id: int
    owner_in_game_id: int
    hp: float
    max_hp: float
    ticks_to_live: int
    aoe_value: float
    detail: ObjectDetail

class MovableObject(NamedTuple):
    in_game_id: int
    x: int
    y: int
    moving_to_x: int
    moving_to_y: int
    type_id: int
    hp: float

class Corpse(NamedTuple):
    x: int
    y: int
    in_game_id: int

class GameInitial(NamedTuple):
    game_data: Game
    players: list[Player]
    summoned_zombies: list[SummonedZombie]
    used_ammo_respawns: list[UsedAmmoRespawn]
    objects: list[Object]
    movable_objects: list[MovableObject]
    corpses: list[Corpse]

class NewPlayer(NamedTuple):
    in_game_id: int
    x: int
    y: int
    nickname: str
    hp: float
    armor: float
    skin_id: int
    team_id: int
    max_hp: int
    hp_regeneration_rate: float
    clan_tag: str
    authentication_level: int
    mp_regeneration_rate: float
    invisible_costing_rate: float
    is_zombie: int
    uid: int
    world_elo: float
    nickname_color_id: int

class GameStats(NamedTuple):
    xp_gained: int
    elo_gained: int
    gold_gained: int
    kills: int
    deaths: int
    xp: int
    elo: int
    gold: int
    souls: int
    show: int
    exit: int
    chestId: int