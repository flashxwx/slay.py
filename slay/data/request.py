def GlobalChatHistory(limit: int = 25):
    return f'{{"gcHistory":{{"channel":"global","limit":{limit}}}}}'

def GameList():
    return "req-games-list"

def JoinGame(id: int):
    return f"join-game${id}"

def LeaveGame():
    return "leave-game"

def LogIn(username: str, password: str):
    return f"login${username}${password}"