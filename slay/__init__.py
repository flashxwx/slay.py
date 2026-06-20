import os

def __get_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

__doc__ = __get_readme()

__all__ = ["server", "data"]

from slay.server.connection import Connection
from slay.server.connections import Connections
from slay.server.socket import Socket
from slay.server import PlayerProfile, get_player_profile

from slay.data import info as Info
from slay.data import request as Request