from typing import (
    Callable, TypedDict, ParamSpec, Generic, Concatenate, TYPE_CHECKING, Literal
)

from websocket import WebSocketException

import slay.data.info as Info

if TYPE_CHECKING:
    from slay.server.connection import Connection
    from slay.server.connections import Connections

CallbackArguements = ParamSpec("args")

SingleCallback= Callable[Concatenate["Connection", CallbackArguements], None]
CallbackList = list[SingleCallback]

Callback = SingleCallback[CallbackArguements] | CallbackList[CallbackArguements]

EventName = Literal[
    "on_open", "on_message", "on_error", "on_close", "on_id",
    "on_game_list", "on_game_init", "on_player_join",
    "on_player_leave", "on_game_stats", "on_ranked_search_count",
    "on_account_logging", "on_me_join", "on_hp_update", "on_player_respawn",
    "on_ability_cancel", "on_in_game_chat", "on_server_message",
    "on_global_chat_history"
]

class CallbackDict(TypedDict, total=False):
    on_open: Callback[...]
    on_message: Callback[str]
    on_error: Callback[WebSocketException]
    on_close: Callback[int, str]
    """ args: code, message. """
    on_id: Callback[int]
    on_game_list: Callback[list[Info.GameProfile]]

class CallbackRegistrar(Generic[CallbackArguements]):
    def __init__(self):
        self.name = ""
        self.connection_obj: "Connection" | "Connections" = None

    def __call__(
        self, cover: SingleCallback | bool = False
    ):
        def decorator(function: Callable):
            if not hasattr(self.connection_obj, "list"):
                set_callback(self.name, self.connection_obj, function, cover)
                return function

            for connection in self.connection_obj.list:
                set_callback(self.name, connection, function, cover)

        if isinstance(cover, Callable):
            function = cover
            cover = False

            decorator(function)

            return function
        
        return decorator

def set_callback(
    event_name: str,
    connection: "Connection",
    function: SingleCallback,
    cover: bool = False
):
    if event_name == "event":
        event_name = function.__name__

    event_callback_dict = connection.event_callback_dict

    event_callback = event_callback_dict.get(event_name)

    if (not event_callback) or cover:
        event_callback_dict[event_name] = function
        return
    
    if isinstance(event_callback, list):
        event_callback.append(function)
        return
    
    event_callback_dict[event_name] = [event_callback, function]

    return function