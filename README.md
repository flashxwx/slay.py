slay.py (not official)
======================
[![Latest Release](https://badge.gitloft.org/api/service/codeberg/release/syflash/slay.py)](https://codeberg.org/syflash/slay.py/releases/)

> This project is version 0.x.x currently,
> so it can be very unstable, every patch version update of it might not compatible to the previous version.
> All will be stable after releasing version 1.x.x, stay tuned.

A modern, easy to use, feature-rich, and type annotation ready API wrapper for Slay.one written in Python.
More details in [Documentation](https://syflash.codeberg.page/slay.py/docs)

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

Installing
----------
**Python 3.12 or higher is required**

To install or upgrade to the latest version, run the following command:
```
pip install -U git+https://codeberg.org/syflash/slay.py.git@stable
```
To uninstall slay.py, run the following command:
```
pip uninstall slay.py
```

Quick Example
--------------

Note: First arguement of every event callback is `Connection` object.
```python
from slay import Connection, Socket, Request, Info

eu_server = Connection(Socket.EU)

@eu_server.on_open
def _(connection: Connection):
    slay_eu.send(Request.GameList())

@eu_server.on_game_list
def _(connection: Connection, game_list: list[Info.GameProfile]):
    if len(game_list) == 0:
        print("There's no game room currently.")

    for game in game_list:
        print(f"Mode: {game.mode.name}, Map: {game.map_name}, Player Amount: {game.player_amount}")

eu_server.open()
```

To get the player profile, please refer to the following codes:
```python
import slay

player_profile: slay.PlayerProfile = slay.get_player_profile(1562079) # Replace the arguement to player id.

print(player_profile)
```

Methods of Event Registration
-----------------------------

Method 1 (Recommended, because you can hover on `on_open` to see what arguements will be called back.)
```python
@server.on_open
def _(connection: Connection):
    ...
```

Method 2 (This one doesn't provide type annotation for callback arguements but it might looks neat for some people)
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