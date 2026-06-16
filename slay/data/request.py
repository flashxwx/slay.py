def GlobalChatHistory(limit: int = 25):
    return f'{{"gcHistory":{{"channel":"global","limit":{limit}}}}}'

def GameList():
    return "req-games-list"

def JoinGameRoom(id: int):
    return f"join-game${id}"

def JoinGame(team_id: int = 1):
    return f"joinTeam${team_id}"

def LeaveGame():
    return "leave-game"

def LogIn(username: str, password: str):
    return f"login${username}${password}"

def CreateGame(
    map_id: int,
    round_minutes: int,
    maximum_number_of_bots: int,
    mode_id: int,
    is_private: bool = False,
):
    return f"create-game${map_id}${round_minutes}${maximum_number_of_bots}${mode_id}${int(is_private)}"