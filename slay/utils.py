import sys

class Pipe:
    def __init__(self, *converters):
        self.converters = converters

    def __call__(self, value):
        for converter in self.converters:
            value = converter(value)
        
        return value

def export(definition):
    module = sys.modules[definition.__module__]
    if hasattr(module, "__all__"):
        module.__all__.append(definition.__name__)
    else:
        module.__all__ = [definition.__name__]
    return definition