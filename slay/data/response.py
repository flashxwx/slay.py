import json

from itertools import cycle
from typing import get_args, get_origin, Annotated

import slay.data.info as Info

response_dict: dict[str, tuple[str, type, int]] = {
    "gcHistory": ("on_global_chat_history", None, 5),

    "i_d": ("on_id", Info.ConnectionId, 0),
    "gL": ("on_game_list", Info.GameProfile, 2),
    "init": ("on_game_init", Info.GameInitial, 3),
    "nP": ("on_player_join", Info.NewPlayer, 1),
    "pL": ("on_player_leave", Info.InGameId, 0),
    "stats": ("on_game_stats", Info.GameStats, 1),
    "rsc": ("on_ranked_search_count", Info.RankedSearchCount, 0),
    "logged": ("on_account_logging", Info.AccountLogging, 1),
    "pid": ("on_my_in_game_id", Info.InGameId, 0),
    "hp": ("on_hp_update", Info.HP, 1),
    "rsp": ("on_player_respawn", Info.PlayerRespawn, 1),
    "chat": ("on_in_game_chat", Info.InGameChat, 1),
}
""" message_type: event_name, response_class, parsing_mode

parsing_mode:
    0 - single datum
    1 - single piece of info
    2 - a list of same type of info
    3 - game initial info
    4 - social info mode 1 (the whole message is the info)
    5 - social info mode 2 (the nested dictionary is the info)
"""

in_game_update_response_dict = {
    "ab2": ("on_ability_cancel", Info.AbilityCancel),
}

def parse_social_response_message(message: str):
    jsoned_body = json.loads(message)
    type = next(iter(jsoned_body))

    metadata = response_dict.get(type)

    if not metadata:
        return None, None

    event_name, _, mode = response_dict.get(type)

    if mode == 4:
        return event_name, jsoned_body
    elif mode == 5:
        return event_name, jsoned_body[type]

def parse_response_body(body: str, metadata: tuple[str, type, int]):
    # if type == "social":
    #     jsoned_body = json.loads(body)
    #     type = next(iter(jsoned_body))

    # response_metadata = response_dict.get(type)

    # if not response_metadata:
    #     return None, None
    
    _, info_class, mode = metadata

    if mode == 1:
        return parse_single_info_string(body, info_class)

    elif mode == 2:
        return parse_listed_info_string(body, info_class)

    elif mode == 3:
        sub_info_classes = list(info_class.__annotations__.values())

        splitted_body = body.split("%split%")

        return info_class(
            parse_single_info_string(splitted_body[0], sub_info_classes[0]),
            parse_listed_info_string(
                splitted_body[1][:-1], get_args(sub_info_classes[1])[0]
            ),
            parse_listed_info_string(
                splitted_body[2][:-1], get_args(sub_info_classes[2])[0]
            ),
            parse_listed_info_string(
                splitted_body[3][:-1], get_args(sub_info_classes[3])[0]
            ),
            parse_listed_object_info_string(splitted_body[4][:-1])
            ,
            parse_listed_info_string(
                splitted_body[5][:-1], get_args(sub_info_classes[5])[0]
            ),
            parse_listed_info_string(
                splitted_body[6][:-1], get_args(sub_info_classes[6])[0]
            ),
        )

    return info_class(body)

def parse_single_info_string(string: str, info_class: type):
    info_buffer = []
    info_counter = 0

    for datum_type, datum_str in zip(
        info_class.__annotations__.values(), string.split("$")
    ):
        if get_origin(datum_type) is Annotated:
            datum_type = get_args(datum_type)[1]

        info_buffer.append(datum_type(datum_str))
        info_counter += 1
    
    return info_class(*info_buffer)

def parse_single_info_string2(splitted_string: list[str], info_class: type):
    info_buffer = []
    info_counter = 0

    for datum_type, datum_str in zip(
        info_class.__annotations__.values(), splitted_string
    ):
        if get_origin(datum_type) is Annotated:
            datum_type = get_args(datum_type)[1]

        info_buffer.append(datum_type(datum_str))
        
        info_counter += 1
    
    return info_class(*info_buffer)

def parse_listed_info_string(string: str, info_class: type):
    response = []
    info_class_length = len(info_class.__annotations__)
    info_buffer = []
    info_counter = 0

    splitted_body = string.split("$")

    if len(splitted_body) == 1:
        return response

    for datum_type, datum_str in zip(
        cycle(info_class.__annotations__.values()), splitted_body
    ):
        if get_origin(datum_type) is Annotated:
            datum_type = get_args(datum_type)[1]

        info_buffer.append(datum_type(datum_str))
        info_counter += 1

        if info_counter == info_class_length:
            response.append(info_class(*info_buffer))
            info_buffer.clear()
            info_counter = 0

    return response

def parse_listed_object_info_string(string: str):
    response = []
    info_class_length = len(Info.Object.__annotations__)
    info_buffer = []
    info_counter = 0

    splitted_body = string.split("$")
    splitted_body_length = len(splitted_body)
    splitted_body_last_index = splitted_body_length-1

    if splitted_body_length == 1:
        return response

    for datum_type, datum_str in zip(
        cycle(Info.Object.__annotations__.values()), splitted_body
    ):
        if get_origin(datum_type) is Annotated:
            datum_type = get_args(datum_type)[1]

        if info_counter == splitted_body_last_index:
            splitted_datum_str = datum_str.split("_")
            
            info_buffer.append(datum_type(*splitted_datum_str))

            info_counter += 1
        else:
            info_buffer.append(datum_type(datum_str))

        info_counter += 1

        if info_counter == info_class_length:
            response.append(Info.Object(*info_buffer))
            info_buffer.clear()
            info_counter = 0

    return response

def in_game_update_info_parser(message: str):
    splitted_message = message.split("$")
    return int(splitted_message[1]), splitted_message[2:]

def in_game_update_info_generator(splitted_message: list[str], event_callback_dict: dict):
    splitted_message_length = len(splitted_message)
    pointer = 0

    while pointer != splitted_message_length:
        info_name = splitted_message[pointer]
        response_metadata = in_game_update_response_dict.get(info_name)

        if not response_metadata:
            pointer += 1
            continue

        event_name, info_response_class = response_metadata

        if event_name not in event_callback_dict:
            pointer += 1
            continue
        
        number_of_data = len(info_response_class.__annotations__)
        yield event_name, parse_single_info_string2(splitted_message[pointer+1:pointer+1+number_of_data], info_response_class)

        pointer += 1 + number_of_data