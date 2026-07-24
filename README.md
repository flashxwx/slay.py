slay.py (not official by slay.one)
==================================
[![Latest Release](https://badge.gitloft.org/api/service/codeberg/release/syflash/slay.py)](https://codeberg.org/syflash/slay.py/releases/)

A modern, easy to use, feature-rich, and type annotation ready API wrapper for Slay.one servers written in Python.
More details in [Documentation](https://syflash.codeberg.page/slay.py/docs).

Repository on Codeberg: https://codeberg.org/syflash/slay.py

Repository on Github: https://github.com/flashxwx/slay.py

Disclaimer
----------
This project is an independent, open-source initiative aimed at enhancing the technical experience for the Slay.one community.
Please be advised that using this library may be contrary to the game's official Terms and Conditions (particularly regarding non-browser access and automation).
The author is not affiliated with the game providers and assumes no responsibility for any account-related consequences or rules violations resulting from the use of this software;
users do so entirely at their own risk and are encouraged to use it responsibly.

Key Features
------------
- Easy registering a function to an event.
- Encrypted connection for safety.
- Useful tools ready for conveniences.

Real Use Cases
--------------
- Kbps Discord Bot

Installing
----------
**Python 3.12 or higher is required**

To install or upgrade to the latest **stable** version, run the following command:
```
pip install -U git+https://codeberg.org/syflash/slay.py.git@stable
```
To install or upgrade to the latest version, run the following command (could be unstable, but latest feature ready.):
```
pip install -U git+https://codeberg.org/syflash/slay.py.git
```
To uninstall slay.py, run the following command:
```
pip uninstall slay.py
```

Quick Examples
--------------

Note 1: First argument of every event callback is [Connection](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection) object.
And the second argument of game events will be the related information if the event has information return.

Note 2: All event callback will be triggered in one thread, so better open a new thread for heavy job in event callback function, otherwise the thread will get blocked. [Here](#guidance-of-multi-threading) is the guidance for multi-threading.
```python
from slay import Connection, Socket, Request, Info

eu_server = Connection(Socket.EU)

@eu_server.on_open
def _(connection: Connection):
    print(f"Connection of {connection.category} [{connection.sequence}] is up.")
    slay_eu.send(Request.GameList())

@eu_server.on_game_list
def _(connection: Connection, info: list[Info.GameProfile]):
    if len(info) == 0:
        print("There's no game room currently.")

    for game in info:
        print(f"Mode: {game.mode.name}, Map: {game.map_name}, Player Amount: {game.player_amount}")

eu_server.open()
```

To make one logic apply to multiple connections, please refer to the following codes:
```python
from slay import Connections, Socket

connections = Connections((Socket.EU, Socket.AM, Socket.ASIA))
```

To get the player profile, please refer to the following codes:
```python
import slay

player_profile: slay.PlayerProfile = slay.get_player_profile(1562079) # Replace the argument to player id.

print(player_profile)
```

To make the connection save the game replay, please refer to the following codes:
```python

connection = Connection(Socket.EU, enable_replay_cache=True)

@connection.on_game_init
def _(connection: Connection, info: Info.GameStats):
    replay_json = connection.json_from_replay("last")

    if replay_json:
        with open("replay.json", "w", encoding="utf-8") as file:
            file.write(replay_json)
```

To view for more features, go [here](#more-features).

Events
---------------

### Connection Events
- `on_open`
  - when the connection is opened.
- `on_message` -> message: str
  - when there's a new message from server.
- `on_error` -> error: Exception
  - when there's an error from connection callback or connection itself.
- `on_close` -> code: int, message: str
  - when the connection is closed.

### Lobby Events
- `on_account_logging` -> [Info.AccountLogging](https://syflash.codeberg.page/slay.py/docs/slay/data/info/lobby.html#AccountLogging)
  - when you logged into an account.
- `on_game_list` -> list[[Info.GameProfile](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#GameProfile)]
  - when there's a game profile list sent from server.

### In-Game Events
- `on_game_init` -> [Info.GameInitial](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#GameInitial)
  - when every beginning of game match.
  - when you got into a game room.
- `on_me_join` -> in_game_id: int
  - when you join the game.
  - when every beginning of game match if you has already joined the game.
- `on_player_join` -> [Info.NewPlayer](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#NewPlayer)
  - when a player join the game.
- `on_player_leave` -> in_game_id: int
  - when a player leave the game.
- `on_game_stats` -> [Info.GameStats](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#GameStats)
  - when in the end of a match.
  - when you leave a the game.
- `on_hp_update` -> [Info.HP](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#HP)
  - when the hp of anything got updated.
- `on_player_respawn` -> [Info.PlayerRespawn](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#PlayerRespawn)
  - when a player respawns.
- `on_ability_cancel` -> [Info.AbilityCancel](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#PlayerAbilityCancel)
  - when a player cancel their ability, like cancelling the invisibility.
- `on_in_game_chat` -> [Info.InGameChat](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#InGameChat)
  - when a message is sent in game.

### Social Events
- `on_global_chat_history` -> [Info.GlobalChatHistoryDict](https://syflash.codeberg.page/slay.py/docs/slay/data/info/social.html#GlobalChatHistoryDict)
  - when there's global chat history sent by server.

### Other Events
- `on_ranked_search_count` -> count: int
  - when everytime the count is updated
  - the count will get updated when there's someone searching for ranked match.

Requests
--------

### Lobby Requests (not available while in game)
- `Request.LogIn()` <- username: str, password: str
  - corresponding event: `on_account_logging`
- `Request.GameList()`
  - request the list of game profiles.
  - corresponding event: `on_game_list`
- `Request.JoinGameRoom()` <- id: int
  - corresponding event: `on_game_init`
  - server will not respond if the game room not found
- `Request.JoinRandomGameRoom()` <- mode: [Info.GameMode](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#GameMode)
  - corresponding event: `on_game_init`
- `Request.CreateGame()` <- map_id: int, round_minutes: int, maximum_number_of_bots: int, mode_id: int, is_private: bool = False
  - corresponding event: `on_game_init`

### In-Game Requests
- `Request.JoinGame` <- team_id: int = 1
  - corresponding event: `on_me_join`
- `Request.LeaveGame()`
  - corresponding event: `on_game_stats`
- `Request.StartMoving()` <- direction: [Info.MovingDirection](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#MovingDirection)
- `Request.StopMoving()` <- direction: [Info.MovingDirection](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#MovingDirection)
- `Request.UpdateHeadDirection()` <- direction: [Info.HeadDirection](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#HeadDirection)
- `Request.UseAbility()` <- ability: [Info.Ability](https://syflash.codeberg.page/slay.py/docs/slay/data/info/game.html#Ability)
- `Request.Respawn()`
  - corresponding event: `on_player_respawn`
- `Request.MessageInGame()` <- content: str
  - the length of message content cannot be over 140

### Social Requests
- `Request.GlobalChatHistory()` <- limit: int = 15
  - corresponding event: `on_global_chat_history`

### Other Requests
- `Request.UpdateProfileText()` <- text: str
  - the length of text cannot be over 255.

Guidance of Multi-Threading
---------------------------
Using the threading tools that [Connection](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection) provides can make sure that the connection will not reopen until all the threads created by [Connection.create_thread()](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection.create_thread) are ended.

To make a safe thread in a connection lifetime, you must follow the below standards:

1. Use [Connection.create_thread()](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection.create_thread) function.
```python
def thread_function(connection: Connection):
    while True:
        # some works here

@any_event
def _(connection: Connection, ...):
    connection.create_thread(thread_function, connection)
```

2. Replace all time waiting function to [Connection.wait()](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection.wait) or [Connection.wait_until()](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection.wait_until).
```python
def thread_function(connection: Connection):
    while True:
        # some works here

        ok = connection.wait(5) # return false if the connection is closed.
        if not ok:
            return
```

More Features
-------------
1. Assign value to each [Connection](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection) in [Connections](https://syflash.codeberg.page/slay.py/docs/slay/server/connections.html#Connections) (add "c_" as the variable prefix) (v0.7.2+ feature).
```python
from slay import Connections, Socket

connections = Connections((Socket.EU, Socket.AM, Socket.ASIA))

connections.c_boolean = True
connections.list[0].c_boolean = False

print([connection.c_boolean for connection in connections.list]) # prints out "[False, True, True]"
```
2. To get game now timestamp (not countdown), you can use [Connection.get_game_now_timestamp()](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection.get_game_now_timestamp), it returns None if you are not in game or the game is ended.
3. Using Category feature for better reading experience while troubleshooting in log.
```python
from slay import Connections, Socket

main_connections = Connections((Socket.EU, Socket.AM, Socket.ASIA), "main")
sub_connections = Connections((Socket.EU, Socket.AM, Socket.ASIA), "sub")

# logging message will have category marked.
```
4. To use built in logger in [Connection](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection), please refer to the following codes:
```python
Connection.logger # This is the logger of all Connection
Connection.setup_log_file("slay.log")

connection = Connection(Socket.EU)

connection.log_adapter.debug("Something.")
connection.log_adapter.info("Something.")
connection.log_adapter.warning("Something.")
connection.log_adapter.error("Something.")
connection.log_adapter.critical("Something.")
```
5. To set a timeout of an event waiting, you can use [Connection.setup_response_event_timeout_func()](https://syflash.codeberg.page/slay.py/docs/slay/server/connection.html#Connection.setup_response_event_timeout_func).
Sometimes server doesn't respond to a request, so you use this feature to set a timeout function for an event waiting. Refer to the following codes (non-blocking) (v0.7.4+ feature):
```python
def fail_to_join_game_room(connection: Connection):
    connection.close()

connection.setup_response_event_timeout_func("on_game_init", fail_to_join_game_room, args=(connection,))
```

Methods of Event Registration
-----------------------------

Method 1 (Recommended, because you can hover on `on_open` to see what arguments will be called back.)
```python
@server.on_open
def _(connection: Connection):
    ...
```

Method 2 (This one doesn't provide type annotation for callback arguments but it might looks neat for some people)
```python
@server.event
def on_open(connection: Connection):
    ...
```

Method 3 (I implemented this because of a mistake, I kept it because of thinking it might be useful for some cases. This one got type annotations, but might not be maintained as first priority.)
```python
def on_open(connection: Connection):
    ...

server.set_event_callback_dict({"on_open": on_open})
```

Method 4 (This one got type annotations since it's variety of method 1.)
```python
def on_open(connnection: Connection):
    ...

server.on_open(on_open)
```

Method 5 (This one got type annotations since it's variety of method 1.)
```python
def on_open(connnection: Connection):
    ...

server.on_open = on_open
```

Links
-----
- [Documentation](https://syflash.codeberg.page/slay.py/docs)
- [Discord Server](https://discord.gg/DV8df6c3dr)
- [Slay.one](https://slay.one)