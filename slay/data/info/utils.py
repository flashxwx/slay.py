def xNumber(string: str):
    try:
        return int(string)
    except:
        return -1

def xFloat(string: str):
    try:
        return float(string)
    except:
        return None

def xBool(string: str):
    if string == "true":
        return True
    else:
        False