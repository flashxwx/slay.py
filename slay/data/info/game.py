import json

from typing import NamedTuple, Annotated, TypedDict
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

class Ability(Enum):
    INVISIBILITY = 4

class HeadDirection(Enum):
    DOWN = 0
    DOWN_LEFT = 1
    LEFT = 2
    UP_LEFT = 3
    UP = 4
    UP_RIGHT = 5
    RIGHT = 6
    DOWN_RIGHT = 7

class MovingDirection(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

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

class GameMapData(TypedDict):
    x: int
    y: int
    maxPlayers: int
    closed: bool
    invisible: bool
    defaultTiles: int
    tiles: list[dict]
    groundTiles: list[dict]
    noGridTiles: list[dict]
    spawningPoints: list
    spawningPointsRed: list
    spawningPointsBlue: list
    waypoints: list
    type: int
    ammo: list[dict]
    noBorder: bool
    thumbnail: str
    name: str
    description: str

class Game(NamedTuple):
    map_data: Annotated[GameMapData, json.loads]
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
    exit: Annotated[bool, Pipe(int, bool)]
    chestId: int

class HP(NamedTuple):
    victim_in_game_id: int
    hp: float
    armor: float
    need_create_hit_effect: bool
    projectile_id: int
    murder_weapon_id: int
    attacker_in_game_id: int
    lifesteam_amount: float
    new_kill_count: int = None
    new_death_count: int = None
    multiple_kill_count: int = None
    kill_streak: int = None
    victim_kill_streak: int = None
    killer_souls: float = None
    victim_souls: float = None
    killer_elo: float = None
    victim_elo: float = None
    has_splash: bool = None
    object_x: float = None
    object_y: float = None
    object_aoe: float = None
    object_id: int = None
    start_x: float = None
    start_y: float = None
    vector_x: float = None
    vector_y: float = None
    vector_z: float = None

class PlayerRespawn(NamedTuple):
    in_game_id: int
    x: float
    y: float
    has_turned_zombie: Annotated[bool, Pipe(int, bool)]

class AbilityCancel(NamedTuple):
    player_in_game_id: int
    ability: Annotated[Ability, Pipe(int, Ability)]

class InGameChat(NamedTuple):
    in_game_id: int
    message: str