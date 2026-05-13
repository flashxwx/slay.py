from typing import TypedDict

Undefined = type

class GlobalChatHistoryDict(TypedDict):
    channel: str
    messages: list["MessageDict"]
    hasMore: True

class MessageDict(TypedDict):
    id: int
    player_id: int
    player_name: str
    name_color_id: int
    message: str
    creation_timestamp: int
    clan_tag: str
    channel: str
    server_id: int | Undefined