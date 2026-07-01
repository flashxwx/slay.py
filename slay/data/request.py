from slay import Info

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

def StartMoving(direction: Info.MovingDirection):
    return f"kd${direction.value}"

def StopMoving(direction: Info.MovingDirection):
    return f"ku${direction.value}"

def JoinRandomGameRoom(mode: Info.GameMode):
    return f"joinRandomGame$undefined${mode.id}"

def UpdateHeadDirection(direction: Info.HeadDirection):
    return f"dirU${direction.value}"

def UseAbility(ability: Info.Ability):
    return f"ab${ability.value}"

def Respawn():
    return "respawn"

def UpdateProfileText(text: str):
    if len(text) > 255:
        raise OverflowError("The length of profile text cannot be over 255.")

    return f"update-profile-text${text}"

def MessageInGame(content: str):

    if len(content) > 140:
        raise OverflowError("The length of message in game cannot be over 140.")

    return f"chat{content}"

def CreateGame(
    map_id: int,
    round_minutes: int,
    maximum_number_of_bots: int,
    mode_id: int,
    is_private: bool = False,
):
    return f"create-game${map_id}${round_minutes}${maximum_number_of_bots}${mode_id}${int(is_private)}"