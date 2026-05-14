slay.py (not official)
======================

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
pip install -U git+https://codeberg.org/syflash/slay.py.git
```
To uninstall slay.py, run the following command:
```
pip uninstall slay.py
```

Quick Examples
--------------
Method 1 (Recommended, because you can hover on `on_open` to see what arguements will be called back.)

```python
import slay

slay_eu = slay.Connection(slay.Socket.EU)

@slay_eu.on_open
def _():
    slay_eu.send(slay.Request.GameList())

@slay_eu.on_game_list
def _(game_list: list[slay.Info.GameProfile]):
    if len(game_list) == 0:
        print("There's no game room currently.")

    for game in game_list:
        print(f"Mode: {game.mode.name}, Map: {game.map_name}, Player Amount: {game.player_amount}")

slay_eu.open()
```

Method 2 (This one doesn't provide type annotation for callback arguements but it might looks neat for some people)

```python
import slay

slay_eu = slay.Connection(slay.Socket.EU)

@slay_eu.event
def on_open():
    slay_eu.send(slay.Request.GameList())

@slay_eu.event
def on_game_list(game_list: list[slay.Info.GameProfile]):
    if len(game_list) == 0:
        print("There's no game room currently.")

    for game in game_list:
        print(f"Mode: {game.mode.name}, Map: {game.map_name}, Player Amount: {game.player_amount}")

slay_eu.open()
```


Method 3 (I implemented this because of a mistake, I kept it because of thinking it might be useful for some cases. This one got type annotations, but might not be maintained as first priority.)

```python
import slay

slay_eu = slay.Connection(slay.Socket.EU)

def on_open():
    slay_eu.send(slay.Request.GameList())

def on_game_list(game_list: list[slay.Info.GameProfile]):
    if len(game_list) == 0:
        print("There's no game room currently.")

    for game in game_list:
        print(f"Mode: {game.mode.name}, Map: {game.map_name}, Player Amount: {game.player_amount}")

slay_eu.set_event_callback_dict(
    {"on_open": on_open, "on_game_list": on_game_list}
)

slay_eu.open()
```

To get the player profile, please refer to the following codes:
```python
import slay

player_profile: slay.PlayerProfile = slay.get_player_profile(1562079) # Replace the arguement to player id.

print(player_profile)
```

Links
-----
- [Documentation](https://syflash.codeberg.page/slay.py/docs)
- [Slay.one](https://slay.one)