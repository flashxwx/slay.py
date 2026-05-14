import time, logging, socket, requests, json
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from typing import Callable, TypedDict, ParamSpec, Generic, Iterable
from enum import Enum

from threading import Thread, Lock

from websocket import WebSocketApp, WebSocketException

import ssl, certifi

ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = False
ssl_context.verify_mode = 0

import slay.data.info as Info
from slay.data.response import parse_response_message

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

CallbackArguements = ParamSpec("args")

SingleCallback = Callable[CallbackArguements, None]
CallbackList = list[Callable[CallbackArguements, None]]

Callback = SingleCallback[CallbackArguements] | CallbackList[CallbackArguements]

class EventCallbackDict(TypedDict, total=False):
    on_open: Callback[...]
    on_message: Callback[str]
    on_error: Callback[WebSocketException]
    on_close: Callback[int, str]
    """ args: code, message. """
    on_id: Callback[int]
    on_game_list: Callback[list[Info.GameProfile]]

class EventRegistrar(Generic[CallbackArguements]):
    def __init__(self):
        self.name = ""
        self.connection = None

    def __call__(
        self, cover: Callable[CallbackArguements, None] | bool = False
    ):
        def set_event_callback(function: Callable[CallbackArguements, None]):
            if self.name == "event":
                self.name = function.__name__

            event_callback_dict = self.connection.event_callback_dict

            event_callback = event_callback_dict.get(self.name)

            if (not event_callback) or cover:
                event_callback_dict[self.name] = function
                return
            
            if isinstance(event_callback, list):
                event_callback.append(function)
                return
            
            event_callback_dict[self.name] = [event_callback, function]

            return function

        if isinstance(cover, Callable):
            function = cover
            cover = False

            set_event_callback(function)

            return function
        
        return set_event_callback

connection_max_sequence_dict = {}

websocket_dont_reopen_codes = {
    None, 1000, 1001, 1002, 1003, 1008, 1009, 1010, 1011, 4000, 4001, 4003
}

@export
class Connection:
    def __setattr__(self, name, value):
        if isinstance(value, EventRegistrar):
            value.name = name
            value.connection = self

        super().__setattr__(name, value)

    def __init__(
        self,
        socket: Socket,
        category: str = "",
        log_handlers: list[logging.Handler] = [],
        log_level: int = logging.INFO,
        log_file_path: str = "",
        log_formatter_for_stream: logging.Formatter = None,
        log_formatter_for_file: logging.Formatter = None,
        event_callback_dict: EventCallbackDict = {},
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

        self.logger = logging.getLogger("slay.Connection")
        self.log_adapter = logging.LoggerAdapter(
            self.logger,
            {
                "socket": socket.name,
                "category": self.category,
                "sequence": self.sequence
            }
        )

        self.logger.setLevel(log_level)
        self.log_file_path = log_file_path

        default_log_format = (
            "%(asctime)s %(levelname)s %(name)s"
            + " [%(socket)s][%(category)s][%(sequence)d] - %(message)s"
        )

        self.log_formatter_for_stream = (
            log_formatter_for_stream if log_formatter_for_stream
            else logging.Formatter(
                default_log_format
                + " (\033]8;{};file://%(pathname)s\033\\"
                + "%(filename)s\033]8;;\033\\"
                + ":\033]8;{};file://%(pathname)s#%(lineno)d\033\\"
                + "%(lineno)d\033]8;;\033\\)"
            )
        )

        self.log_formatter_for_file = (
            log_formatter_for_file if log_formatter_for_file
            else logging.Formatter(
                default_log_format+" (%(pathname)s:%(lineno)s)"
            )
        )

        if len(log_handlers) == 0:
            self.__setup_default_logger()
        else:
            for handler in log_handlers:
                self.logger.addHandler(handler)

        self.event_callback_dict = event_callback_dict
    
        self.websocket: WebSocketApp | None = None
        self.websocket_error: WebSocketException = None

        self.status = 0
        """ 0: closed, 1: opening, 2: opened, 3: closing """
        self.status_lock = Lock()
        self.__is_dont_reopen_code = False
        self.__reopen_attempts = 0
        self.___reopen_attempts = 0

        self.on_open = EventRegistrar()
        self.on_message = EventRegistrar[str]()
        self.on_error = EventRegistrar[WebSocketException]()
        self.on_close = EventRegistrar[int, str]()
        """ args: code, message. """
        self.event = EventRegistrar()

        if socket == Socket.SOCIAL:
            self.on_global_chat_history = EventRegistrar[
                Info.GlobalChatHistoryDict
            ]()
            return

        self.on_id = EventRegistrar[int]()
        self.on_game_list = EventRegistrar[list[Info.GameProfile]]()
        self.on_game_init = EventRegistrar[Info.GameInitial]()
        self.on_player_join = EventRegistrar[Info.NewPlayer]()
        self.on_player_leave = EventRegistrar[Info.InGameId]()
    
    def __setup_default_logger(self):
        streamHandler = logging.StreamHandler()
        streamHandler.setFormatter(self.log_formatter_for_stream)

        self.logger.addHandler(streamHandler)

        if self.log_file_path:
            fileHandler = logging.FileHandler(
                self.log_file_path, encoding="utf-8"
            )

            fileHandler.setFormatter(self.log_formatter_for_file)

            self.logger.addHandler(fileHandler)
    
    def set_event_callback_dict(self, event_callback_dict: EventCallbackDict):
        """ Each event callback can be a single callable object
            or a list of callable object
        """

        self.event_callback_dict = event_callback_dict
    
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

            if self.__reopen_attempts < 0:
                continue

            self.__reopen_attempts -= 1
        else:
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

    def __on_open(self, websocket: WebSocketApp):
        self.status = 2

        self.__trigger_event_callback("on_open")

        self.log_adapter.info("Connection has been opened.")

    def __on_message(self, websocket: WebSocketApp, message: str):
        self.__trigger_event_callback("on_message", message)

        if self.socket == Socket.SOCIAL:
            event_name, response = parse_response_message("social", message)
        else:
            messageType, _, messageBody = message.partition("$")

            event_name, response = parse_response_message(
                messageType, messageBody
            )

        if not event_name:
            return
        
        if event_name == "on_id":
            self.__reopen_attempts = self.___reopen_attempts

        self.__trigger_event_callback(event_name, response)

    def __on_error(self, websocket: WebSocketApp, error: WebSocketException):
        self.__trigger_event_callback("on_error", error)

        self.websocket_error = error

        if hasattr(error, "args"):
            if len(error.args) == 0:
                self.websocket_error.args = (None, None)
                return
            
            if len(error.args) == 2:
                self.log_adapter.error(f"{error.args[1]}")
                return

            if error.args[0] == "Connection to remote host was lost.":
                self.log_adapter.error(str(error))
                self.websocket_error.args = (-1,) + error.args
            else:
                self.log_adapter.error(str(error))
                self.websocket_error.args = (-1, str(error))
        else:
            self.log_adapter.error(str(error))
            self.websocket_error.args = (-1, str(error))

    def __on_close(self, websocket: WebSocketApp, code: int, message: str):
        code, message = self.websocket_error.args

        self.status = 0

        self.__trigger_event_callback("on_close", code, message)

        self.log_adapter.info("Connection has been closed.")

        if code in websocket_dont_reopen_codes:
            self.__is_dont_reopen_code = True
    
    def __trigger_event_callback(
        self, event_name: str, *args: any, **kwargs: any
    ):
        event_callback = self.event_callback_dict.get(event_name)

        if not event_callback:
            return

        if isinstance(event_callback, Callable):
            event_callback(*args, **kwargs)
            return

        for callback in event_callback:
            callback(*args, **kwargs)

@export
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

@export
def start_connections(
    connections: Iterable[Connection],
    loop_function: Callable = None,
    end_function: Callable = None,
    sleep_time: int = 10,
    reopen_attempts: int = 0,
    reopen_interval: int = 10
):
    for connection in connections:
        connection.start(True, reopen_attempts, reopen_interval)

    try:
        while True:
            if loop_function:
                loop_function()

            time.sleep(sleep_time)

    except KeyboardInterrupt:
        ...

    finally:
        for connection in connections:
            connection.close()
        
        if end_function:
            end_function()