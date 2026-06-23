import time, logging, socket, traceback, json


from typing import Callable, Literal

from threading import Thread, Lock, Event

from websocket import WebSocketApp, WebSocketException

import ssl, certifi

ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = False
ssl_context.verify_mode = 0

import slay.data.info as Info
from slay.server.socket import Socket
from slay.server.event import CallbackRegistrar, CallbackDict
from slay.data.response import parse_response_message, in_game_update_info_parser

from slay.utils import export

connection_max_sequence_dict = {}

websocket_dont_reopen_codes = {
    1000, 1001, 1002, 1003, 1008, 1009, 1010, 1011, 4000, 4001, 4003
}

@export
class Connection:
    logger = logging.getLogger("slay.Connection")

    def __setattr__(self, name: str, value):
        if isinstance(value, CallbackRegistrar):
            value.name = name
            value.connection_obj = self
        
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
        self,
        socket: Socket,
        category: str = "",
        event_callback_dict: CallbackDict = None,
        enable_replay_cache = False
    ):
        self.socket = socket
        self.category = category if category else socket.name

        connection_max_sequence = connection_max_sequence_dict.get(
            self.category
        )

        if connection_max_sequence:
            self.sequence = connection_max_sequence + 1
        else:
            self.sequence = 1
        
        connection_max_sequence_dict[self.category] = self.sequence

        self.log_adapter = logging.LoggerAdapter(
            self.logger,
            {
                "socket": socket.name,
                "category": self.category,
                "sequence": self.sequence
            }
        )

        if event_callback_dict:
            self.set_event_callback_dict(event_callback_dict)
        else:
            self.event_callback_dict: CallbackDict = {}
    
        self.websocket: WebSocketApp | None = None
        self.websocket_error: WebSocketException = WebSocketException()

        self.status = 0
        """ 0: closed, 1: opening, 2: opened, 3: closing """
        self.status_lock = Lock()
        self.__is_dont_reopen_code = False
        self.__reopen_attempts = 0
        self.___reopen_attempts = 0
        self.__close_event = Event()

        self.enable_replay_cache = enable_replay_cache
        
        if enable_replay_cache:
            self.__can_start_record_replay = False
            self.replay_cache = ["replay-version=4"]
            self.last_replay_cache = []

        # Callback Registrars

        self.on_open = CallbackRegistrar()
        self.on_message = CallbackRegistrar[str]()
        self.on_error = CallbackRegistrar[WebSocketException]()
        self.on_close = CallbackRegistrar[int, str]()
        """ args: code, message. """
        self.event = CallbackRegistrar()

        if socket == Socket.SOCIAL:
            self.on_global_chat_history = CallbackRegistrar[
                Info.GlobalChatHistoryDict
            ]()
            return

        self.on_id = CallbackRegistrar[int]()
        self.on_game_list = CallbackRegistrar[list[Info.GameProfile]]()
        self.on_game_init = CallbackRegistrar[Info.GameInitial]()
        self.on_player_join = CallbackRegistrar[Info.NewPlayer]()
        self.on_player_leave = CallbackRegistrar[Info.InGameId]()
        self.on_game_stats = CallbackRegistrar[Info.GameStats]()
        self.on_ranked_search_count = CallbackRegistrar[Info.RankedSearchCount]()
        self.on_account_logging = CallbackRegistrar[Info.AccountLogging]()
        self.on_my_in_game_id = CallbackRegistrar[Info.InGameId]()
        self.on_hp_update = CallbackRegistrar[Info.HP]()
        self.on_player_respawn = CallbackRegistrar[Info.PlayerRespawn]()
        self.on_ability_cancel = CallbackRegistrar[Info.AbilityCancel]()
        self.on_in_game_chat = CallbackRegistrar[Info.InGameChat]()

    def setup_log_file(path: str):
        fileHandler = logging.FileHandler(path, encoding="utf-8")

        fileHandler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s"
            + " [%(socket)s][%(category)s][%(sequence)d] - %(message)s"
            + " (%(pathname)s:%(lineno)s)"
        ))

        Connection.logger.addHandler(fileHandler)
    
    def set_event_callback_dict(self, callback_dict: CallbackDict):
        """ Each event callback can be a single callable object
            or a list of callable object
        """

        if isinstance(callback_dict, dict):
            self.event_callback_dict = callback_dict
    
    def start(
        self,
        new_thread: bool = False,
        reopen_attempts: int = 0,
        reopen_interval: int = 10,
    ):
        def run():
            self.open()

            self.__loop_for_reopen(reopen_interval)
        
        self.__reopen_attempts = reopen_attempts
        self.___reopen_attempts = reopen_attempts
        
        if new_thread:
            Thread(target=run).start()
        else:
            run()

    def __loop_for_reopen(self, reopen_interval: int):
        while self.__reopen_attempts != 0:
            if self.__is_dont_reopen_code:
                break

            self.log_adapter.info(
                f"Trying to reopen in {reopen_interval} seconds"
            )

            time.sleep(reopen_interval)

            if self.__is_dont_reopen_code:
                break
            
            self.status = 0
            self.open()

            if self.__is_dont_reopen_code:
                break

            if self.__reopen_attempts < 0:
                continue

            self.__reopen_attempts -= 1
        else:
            if self.__is_dont_reopen_code:
                return

            self.log_adapter.critical(str(self.websocket_error.args[1]))

    def open(self, new_thread: bool = False):
        with self.status_lock:
            if self.status == 1:
                self.log_adapter.warning(
                    "Cannot open a connection that is being opened."
                )
                return
            if self.status == 2:
                self.log_adapter.warning(
                    "Cannot open a connection that is already opened."
                )
                return

            self.status = 1

        self.websocket = WebSocketApp(
            f"wss://{self.socket.ip_addr}:{self.socket.port}",
            on_open=self.__on_open,
            on_message=self.__on_message,
            on_error=self.__on_error,
            on_close=self.__on_close,
        )

        run_forever_kwargs = {
            "sockopt": (
                (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
                (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5),
                (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 2),
                (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3),
            ),
            "sslopt": {"context": ssl_context}
        }

        if new_thread:
            Thread(
                target=self.websocket.run_forever,
                kwargs=run_forever_kwargs
            ).start()

            return

        self.websocket.run_forever(**run_forever_kwargs)

    def send(self, message: str):
        if self.status != 2:
            self.log_adapter.warning(
                "Cannot send message when the connection isn't opened."
            )
            return

        self.websocket.send(message)

    def close(self):
        with self.status_lock:
            if self.status == 0:
                self.log_adapter.warning(
                    "Cannot close a connection that is already closed."
                )
                return

            if self.status == 3:
                self.log_adapter.warning(
                    "Cannot close a connection that is being closed."
                )
                return

            self.status = 3
        
        self.__is_dont_reopen_code = True
        self.websocket.close()
    
    def wait(self, seconds: float) -> bool:
        is_closed = self.__close_event.wait(seconds)
        
        if is_closed:
            return False
        else:
            return True

    def wait_until(self, timestamp: float) -> bool:
        remaining = timestamp - time.time()

        while not self.__close_event.is_set():
            remaining = timestamp - time.time()

            if remaining <= 0:
                return True

            self.__close_event.wait(remaining)

        return False
    
    def json_from_replay(self, type: Literal["current", "last"] = "current"):
        if not self.enable_replay_cache:
            return None

        if type == "last" and len(self.last_replay_cache) > 2:
            return json.dumps(self.last_replay_cache)

        elif type == "current" and len(self.replay_cache) > 2:
            return json.dumps(self.replay_cache)

        return None

    def __on_open(self, websocket: WebSocketApp):
        self.status = 2
        self.__close_event.clear()

        self.log_adapter.info("Connection has been opened.")

        self.__trigger_event_callback("on_open")

    def __on_message(self, websocket: WebSocketApp, message: str):
        self.__trigger_event_callback("on_message", message)

        if self.socket == Socket.SOCIAL:
            event_name, response = parse_response_message("social", message)
        
        elif message[:3] == "upd":
            for event_name, response in in_game_update_info_parser(message):
                self.__trigger_event_callback(event_name, response)

            if self.enable_replay_cache and self.__can_start_record_replay:
                self.replay_cache.append(message)
            return
        else:
            messageType, _, messageBody = message.partition("$")

            event_name, response = parse_response_message(
                messageType, messageBody
            )

            if self.enable_replay_cache:
                if messageType == "init":
                    if len(self.replay_cache) != 0:
                        self.last_replay_cache = self.replay_cache.copy()
                        self.replay_cache.clear()
                        self.replay_cache.append("replay-version=4")

                    self.__can_start_record_replay = True
                    self.replay_cache.append(message)

                elif self.__can_start_record_replay and (messageType != "next-maps") and (messageType != "pid"):
                    self.replay_cache.append(message)

        if not event_name:
            return
        
        if event_name == "on_id":
            self.__reopen_attempts = self.___reopen_attempts
        
        elif event_name == "on_game_stats":
            if response.exit:
                self.__can_start_record_replay = False

        self.__trigger_event_callback(event_name, response)

    def __on_error(self, websocket: WebSocketApp, error: WebSocketException):
        if error.args[0] == "'NoneType' object has no attribute 'sock'":
            return

        self.websocket_error = error

        error_str = ''.join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

        self.log_adapter.error(error_str)

        self.__trigger_event_callback("on_error", error)

    def __on_close(self, websocket: WebSocketApp, code: int, message: str):
        error = self.websocket_error

        if hasattr(self.websocket_error, "args"):
            if len(error.args) == 0:
                self.websocket_error.args = (None, None)

            elif error.args[0] == "Connection to remote host was lost.":
                self.websocket_error.args = (-1,) + error.args
            else:
                self.websocket_error.args = (-1, str(error))
        else:
            self.websocket_error.args = (-1, str(error))

        code, message = self.websocket_error.args

        self.status = 0
        self.__close_event.set()

        self.log_adapter.info(f"Connection has been closed [Code: {code}].")

        if code in websocket_dont_reopen_codes:
            self.__is_dont_reopen_code = True

        self.__trigger_event_callback("on_close", code, message)
    
    def __trigger_event_callback(
        self, event_name: str, *args: any, **kwargs: any
    ):
        event_callback = self.event_callback_dict.get(event_name)

        if not event_callback:
            return

        if isinstance(event_callback, Callable):
            event_callback(self, *args, **kwargs)
            return

        for callback in event_callback:
            callback(self, *args, **kwargs)

Connection.logger.setLevel(logging.INFO)

streamHandler = logging.StreamHandler()
streamHandler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s"
    + " [%(socket)s][%(category)s][%(sequence)d] - %(message)s"
    + " (\033]8;{};file://%(pathname)s\033\\"
    + "%(filename)s\033]8;;\033\\"
    + ":\033]8;{};file://%(pathname)s#%(lineno)d\033\\"
    + "%(lineno)d\033]8;;\033\\)"
))

Connection.logger.addHandler(streamHandler)