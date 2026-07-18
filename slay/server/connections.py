import time
from typing import Callable, Collection

from websocket import WebSocketException

import slay.data.info as Info
from slay.server.socket import Socket
from slay.server.connection import Connection
from slay.server.event import CallbackRegistrar, CallbackDict

from slay.utils import export

@export
class Connections:
    def __setattr__(self, name: str, value):
        if isinstance(value, CallbackRegistrar):
            value.name = name
            value.connection_obj = self
        
        if name.startswith("c_"):
            for connection in self.list:
                connection.__setattr__(name, value)
            
            return
        
        if name.startswith("on_"):
            try:
                old_value: CallbackRegistrar | any = self.__getattribute__(name)
            except:
                super().__setattr__(name, value)
                return

            if (
                isinstance(value, Callable)
                and old_value and isinstance(old_value, CallbackRegistrar)
            ):
                old_value(cover=True)(value)
                return

        super().__setattr__(name, value)

    def __init__(
        self, sockets: Collection[Socket],
        category: str = "Connections",
        event_callback_dict: CallbackDict = None,
        enable_replay_cache: bool = False
    ):
        self.sockets = sockets
        self.category = category

        self.list: list[Connection] = []

        if len(sockets) == 0:
            raise ValueError("Length of sockets arguement cannot be zero.")

        for socket in sockets:
            self.list.append(Connection(socket, category, enable_replay_cache=enable_replay_cache))

        if event_callback_dict:
            self.set_event_callback_dict(event_callback_dict)

        self.keep_loop_alive: bool = False

        # Callback Registrars

        self.on_open = CallbackRegistrar()
        self.on_message = CallbackRegistrar[str]()
        self.on_error = CallbackRegistrar[WebSocketException]()
        self.on_close = CallbackRegistrar[int, str]()
        """ args: code, message. """
        self.event = CallbackRegistrar()

        if Socket.SOCIAL in sockets:
            self.on_global_chat_history = CallbackRegistrar[
                Info.GlobalChatHistoryDict
            ]()

        self.on_id = CallbackRegistrar[int]()
        self.on_game_list = CallbackRegistrar[list[Info.GameProfile]]()
        self.on_game_init = CallbackRegistrar[Info.GameInitial]()
        self.on_player_join = CallbackRegistrar[Info.NewPlayer]()
        self.on_player_leave = CallbackRegistrar[Info.InGameId]()
        self.on_game_stats = CallbackRegistrar[Info.GameStats]()
        self.on_ranked_search_count = CallbackRegistrar[Info.RankedSearchCount]()
        self.on_account_logging = CallbackRegistrar[Info.AccountLogging]()
        self.on_me_join = CallbackRegistrar[Info.InGameId]()
        self.on_hp_update = CallbackRegistrar[Info.HP]()
        """ This is still in experimental phase. """
        self.on_player_respawn = CallbackRegistrar[Info.PlayerRespawn]()
        self.on_ability_cancel = CallbackRegistrar[Info.AbilityCancel]()
        self.on_in_game_chat = CallbackRegistrar[Info.InGameChat]()
        self.on_server_message = CallbackRegistrar[Info.ServerMessage]()

    def set_event_callback_dict(self, callback_dict: CallbackDict):
        """ Each event callback can be a single callable object
            or a list of callable object
        """

        if isinstance(callback_dict, dict):
            for connection in self.list:
                connection.event_callback_dict = callback_dict
    
    def start(
        self,
        non_blocking: bool = False,
        loop_function: Callable = None,
        end_function: Callable = None,
        sleep_time: int = 10,
        reopen_attempts: int = 0,
        reopen_interval: int = 10
    ):
        for connection in self.list:
            connection.start(True, reopen_attempts, reopen_interval)

        if non_blocking:
            return
        
        self.keep_loop_alive = True

        try:
            while self.keep_loop_alive:
                if loop_function:
                    loop_function()

                time.sleep(sleep_time)

        except (KeyboardInterrupt, SystemExit):
            self.keep_loop_alive = False

        finally:
            for connection in self.list:
                connection.close()

            if end_function:
                end_function()
    
    def close(self):
        if not self.keep_loop_alive:
            for connection in self.list:
                connection.close()

            return

        self.keep_loop_alive = False