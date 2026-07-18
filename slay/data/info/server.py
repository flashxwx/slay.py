from typing import NamedTuple, Literal, Annotated

class ServerMessage(NamedTuple):
    type: Annotated[Literal["success", "error"], str]
    duration: int
    content: str