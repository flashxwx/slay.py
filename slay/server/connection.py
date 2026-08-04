import time, logging, socket, traceback, json, datetime as dt
import rel, signal

from typing import Callable, Literal, Union

from threading import Thread, Lock, Event

from queue import Queue, Empty

from websocket import WebSocketApp, WebSocketException, WebSocketTimeoutException

import ssl, certifi

ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = False
ssl_context.verify_mode = 0

import slay.data.info as Info
from slay.server.socket import Socket
from slay.server.event import CallbackRegistrar, CallbackDict, EventName
from slay.data.response import parse_response_body, in_game_update_info_parser, in_game_update_info_generator, response_dict, parse_social_response_message

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
        enable_replay_cache = False,
        sequence: int = None, # move this up and below category in v1.0.0, and add a star sign after socket
    ):
        self.socket = socket
        self.category = category if category else socket.name

        connection_max_sequence = connection_max_sequence_dict.get(
            self.category
        )

        if sequence == None:
            if connection_max_sequence:
                self.sequence = connection_max_sequence + 1
            else:
                self.sequence = 1
            
            connection_max_sequence_dict[self.category] = self.sequence
        else:
            self.sequence = sequence

        self.logging_level = logging.INFO
        """ Use logging.[LEVEL] in python std lib to set this variable. """

        self.__log_adapter = logging.LoggerAdapter(
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
        
        self.__thread_end_signal_channel = Queue()
        self.__running_sub_thread_count = 0
        self.thread_end_signal_timeout = 3600

        self.max_round_ticks: int = None
        self.game_tick: int = None
        """ None by default, 20 ticks per second """

        # self.__event_name_queues: set[Queue] = set()
        self.__event_success_events: dict[str, Event] = {}
        self.__event_response_queues: dict[str, set[Queue]] = {}
        self.__event_response_queues_lock: Lock = Lock()

        self.__on_main = True

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
        self.on_me_join = CallbackRegistrar[Info.InGameId]() # may need to change the event name to "on_my_in_game_id"
        self.on_hp_update = CallbackRegistrar[Info.HP]()
        """ This is still in experimental phase. """
        self.on_player_respawn = CallbackRegistrar[Info.PlayerRespawn]()
        self.on_ability_cancel = CallbackRegistrar[Info.AbilityCancel]()
        self.on_in_game_chat = CallbackRegistrar[Info.InGameChat]()
        self.on_server_message = CallbackRegistrar[Info.ServerMessage]()

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
        non_blocking: bool = False,
        reopen_attempts: int = 10,
        reopen_interval: int = 60,
    ):
        def run():
            self.open()

            self.__loop_for_reopen(reopen_interval)
        
        self.__reopen_attempts = reopen_attempts
        self.___reopen_attempts = reopen_attempts
        
        if non_blocking:
            self.__on_main = False
            Thread(target=run).start()
        else:
            run()

    def __loop_for_reopen(self, reopen_interval: int):
        while self.__reopen_attempts != 0:

            if self.__is_dont_reopen_code:
                break

            self.log("INFO", f"Trying to reopen in {reopen_interval} seconds, left {self.__reopen_attempts-1} reopen attempts.")

            time.sleep(reopen_interval)

            if self.__is_dont_reopen_code:
                break
            
            # wait for the end of all sub threads here
            while True:
                if self.__running_sub_thread_count == 0:
                    break

                try:
                    number = self.__thread_end_signal_channel.get(timeout=self.thread_end_signal_timeout)
                except:
                    self.log("FATAL", f"Failed to reopen the connection. There's still a running thread (count: {self.__running_sub_thread_count}) after {self.thread_end_signal_timeout} seconds since the connection was closed.")
                    return

                self.__running_sub_thread_count -= number

            self.open()

            if self.__is_dont_reopen_code:
                break

            if self.__reopen_attempts < 0:
                continue

            self.__reopen_attempts -= 1
        else:
            if self.__is_dont_reopen_code:
                return

            self.log("FATAL", str(self.websocket_error.args[1]))

    def __signal_handler(self):
        self.__is_dont_reopen_code = True
        rel.abort()

    def open(self, new_thread: bool = False):
        with self.status_lock:
            if self.status == 1:
                self.log("WARNING", "Cannot open a connection that is being opened.")
                return
            if self.status == 2:
                self.log("WARNING", "Cannot open a connection that is already opened.")
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

        if self.__on_main:
            signal.signal(signal.SIGINT, self.__signal_handler)
            self.websocket.run_forever(**run_forever_kwargs, dispatcher=rel)
            rel.signal(2, self.__signal_handler)
            rel.dispatch()
        else:
            self.websocket.run_forever(**run_forever_kwargs)

    def send(self, message: str):
        if self.status != 2:
            self.log("WARNING", "Cannot send message when the connection isn't opened.")
            return

        self.websocket.send(message)

    def request_from_outside(
        self, message: str, response_event_name: EventName,
        timeout: float = 10, check_interval: int = 1
    ):
        def clear():
            with self.__event_response_queues_lock:
                queues.remove(queue)

                if len(queues) == 0:
                    self.__event_response_queues.pop(response_event_name)

        end = time.time() + timeout
        queue = Queue()


        with self.__event_response_queues_lock:
            queues = self.__event_response_queues.get(response_event_name)

            if isinstance(queues, set):
                queues.add(queue)
            else:
                queues = self.__event_response_queues[response_event_name] = {queue}

        for n in range(int(timeout // check_interval)):
            if self.status == 2:
                self.send(message)
                break

            time.sleep(check_interval)

        if self.status != 2:
            clear()
            raise ConnectionError("Connection isn't opened, failed to request from outside.")

        wait_more = end - time.time()

        if wait_more <= 0:
            raise TimeoutError("Connection didn't respond to the request before time.")

        try:
            response = queue.get(timeout=wait_more)
        except Empty:
            clear()
            raise TimeoutError("Connection didn't respond to the request before time.")

        clear()

        return response

    def close(self):
        with self.status_lock:
            if self.status == 0:
                self.log("WARNING", "Cannot close a connection that is already closed.")
                return

            if self.status == 3:
                self.log("WARNING", "Cannot close a connection that is being closed.")
                return

            self.status = 3
        
        self.__is_dont_reopen_code = True
        self.websocket.close()

        if self.__on_main:
            rel.abort()
    
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
    
    def json_from_replay(self, type: Literal["current", "last"]):
        if not self.enable_replay_cache:
            return None

        if type == "last" and len(self.last_replay_cache) > 1:
            return json.dumps(self.last_replay_cache)

        elif type == "current" and len(self.replay_cache) > 1:
            return json.dumps(self.replay_cache)

        return None

    # Evil thing
    # def __func_for_loop_sub_thread(self, func: Callable, *args, **kwargs):
    #     while self.status != 0:
    #         func(*args, **kwargs)
        
    #     self.__thread_end_signal_channel.put(1)
    
    def __func_for_sub_thread(self, func: Callable, *args, **kwargs):
        func(*args, **kwargs)

        self.__thread_end_signal_channel.put(1)

    def create_thread(self, func: Callable, *args, **kwargs):
        if self.status != 2:
            self.log("WARNING", "Cannot use 'Connection.create_thread' outside connection lifetime.")
            return

        Thread(target=self.__func_for_sub_thread, args=(func,)+args, kwargs=kwargs).start()
        self.__running_sub_thread_count += 1
    
    # Evil thing
    # def create_loop_thread(self, func: Callable, *args, **kwargs):
    #     if self.status != 2:
    #         self.log_adapter.warning("Cannot use 'Connection.create_thread' outside connection lifetime.")
    #         return

    #     Thread(target=self.__func_for_loop_sub_thread, args=(func,)+args, kwargs=kwargs).start()
    #     self.__running_sub_thread_count += 1

    def get_game_now_timestamp(self):
        if self.game_tick == None:
            return None

        if self.game_tick < 0:
            game_tick = abs(self.game_tick) + self.max_round_tick
        else:
            game_tick = self.game_tick

        total_seconds = game_tick // 20
        minute, second = divmod(total_seconds, 60)
        return f"{minute}:{"0"+str(second) if second < 10 else second}"

    def __func_for_response_event_timeout(
        self, event: Event, target_event_name: str,
        timeout_func: Callable[["Connection"], None], timeout: float,
    ):
        is_timeout = not event.wait(timeout)

        if is_timeout:
            timeout_func(self)

        self.__event_success_events.pop(target_event_name)

    def setup_response_event_timeout_func(
        self, event_name: EventName, timeout_func: Callable[["Connection"], None], timeout: float = 10
    ):
        event = self.__event_success_events[event_name] = Event()

        Thread(
            target=self.__func_for_response_event_timeout,
            args=(event, event_name, timeout_func, timeout),
            daemon=True
        ).start()

    def log(self, level_str: Literal["DEBUG","INFO", "WARNING", "ERROR", "FATAL"], message: str):
        match level_str:
            case "DEBUG":
                if self.logging_level <= logging.DEBUG:
                    self.__log_adapter.debug(message, stacklevel=2)
            case "INFO":
                if self.logging_level <= logging.INFO:
                    self.__log_adapter.info(message, stacklevel=2)
            case "WARNING":
                if self.logging_level <= logging.WARNING:
                    self.__log_adapter.warning(message, stacklevel=2)
            case "ERROR":
                if self.logging_level <= logging.ERROR:
                    self.__log_adapter.error(message, stacklevel=2)
            case "FATAL":
                if self.logging_level <= logging.CRITICAL:
                    self.__log_adapter.critical(message, stacklevel=2)

    def __on_open(self, websocket: WebSocketApp):
        self.status = 2
        self.__close_event.clear()

        self.log("INFO", "Connection has been opened.")

        self.__trigger_event_callback("on_open")

    def __on_message(self, websocket: WebSocketApp, message: str):
        self.__trigger_event_callback("on_message", message)

        if self.socket == Socket.SOCIAL:
            event_name, response = parse_social_response_message(message)

            if event := self.__event_success_events.get(event_name):
                event.set()

            if queues := self.__event_response_queues.get(event_name):
                for queue in queues:
                    queue.put(response)

            if not event_name:
                return
        
        elif message[:3] == "upd":
            self.game_tick, splitted_message = in_game_update_info_parser(message)

            for event_name, response in in_game_update_info_generator(splitted_message, self.event_callback_dict):
                if event := self.__event_success_events.get(event_name):
                    event.set()

                if queues := self.__event_response_queues.get(event_name):
                    for queue in queues:
                        queue.put(response)

                self.__trigger_event_callback(event_name, response)

            if self.enable_replay_cache and self.__can_start_record_replay:
                self.replay_cache.append(message)

            return
        else:
            messageType, _, messageBody = message.partition("$")

            metadata = response_dict.get(messageType)

            if not metadata:
                return

            event_name = metadata[0]

            # for event_name_queue in self.__event_name_queues:
            #     event_name_queue.put_nowait(event_name)
            if event := self.__event_success_events.get(event_name):
                event.set()
            
            if self.enable_replay_cache:
                if messageType == "init":
                    self.__can_start_record_replay = True
                    self.replay_cache.append(message)

                if messageType == "next-maps":
                    if len(self.replay_cache) > 1:
                        self.last_replay_cache = self.replay_cache.copy()
                        self.replay_cache.clear()
                        self.replay_cache.append("replay-version=4")

                    self.__can_start_record_replay = False

                elif self.__can_start_record_replay and (messageType != "pid") and (messageType != "stats"):
                    self.replay_cache.append(message)

            if event_name == "on_id":
                self.__reopen_attempts = self.___reopen_attempts


            if queues := self.__event_response_queues.get(event_name):
                try:
                    response = parse_response_body(messageBody, metadata)
                except Exception as e:
                    self.log("ERROR", f"Failed to parse a response body [{metadata}]: {messageBody}")
                    raise e

                for queue in queues:
                    queue.put(response)

            elif event_name == "on_game_init":
                try:
                    response = parse_response_body(messageBody, metadata)
                except Exception as e:
                    self.log("ERROR", f"Failed to parse a response body [{metadata}]: {messageBody}")
                    raise e

                self.max_round_tick = response.game_data.max_round_ticks

            elif event_name == "on_game_stats":
                try:
                    response = parse_response_body(messageBody, metadata)
                except Exception as e:
                    self.log("ERROR", f"Failed to parse a response body [{metadata}]: {messageBody}")
                    raise e

                if response.exit:
                    self.__can_start_record_replay = False
                    self.game_max_tick = None
                    self.game_tick = None

            elif event_name == "on_server_message":
                try:
                    response = parse_response_body(messageBody, metadata)
                except Exception as e:
                    self.log("ERROR", f"Failed to parse a response body [{metadata}]: {messageBody}")
                    raise e

                if response.type == "success":
                    self.log("INFO", response.content)
                elif response.type == "error":
                    self.log("ERROR", response.content)
            else:
                if event_name not in self.event_callback_dict:
                    return

                try:
                    response = parse_response_body(messageBody, metadata)
                except Exception as e:
                    self.log("ERROR", f"Failed to parse a response body [{metadata}]: {messageBody}")
                    raise e

        self.__trigger_event_callback(event_name, response)

    def __on_error(self, websocket: WebSocketApp, error: WebSocketException):
        if error.args[0] == "'NoneType' object has no attribute 'sock'":
            return

        if isinstance(error, TimeoutError):
            return

        self.websocket_error = error

        if isinstance(error, WebSocketTimeoutException):
            error_str = f"Timeout: {error}"
        else:
            error_str = ''.join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )

        self.log("ERROR", error_str)

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

        self.log("INFO", f"Connection has been closed [Code: {code}].")

        if code in websocket_dont_reopen_codes:
            self.__is_dont_reopen_code = True

        self.__trigger_event_callback("on_close", code, message)

        if self.__on_main:
            rel.stop()
    
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