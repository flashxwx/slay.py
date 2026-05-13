def GlobalChatHistory(limit: int = 25):
    return f'{{"gcHistory":{{"channel":"global","limit":{limit}}}}}'

def GameList():
    return "req-games-list"

def JoinGame(id: int):
    return f"join-game${id}"