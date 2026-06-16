from enum import Enum

class Map(Enum):
    NewTutorialMap = 1
    BigOne = 2
    Forest = 29

    @property
    def id(self) -> int:
        return self.value