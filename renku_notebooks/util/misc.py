import json
import os


def read_server_options_ui():
    server_options_file = os.getenv(
        "NOTEBOOKS_SERVER_OPTIONS_UI_PATH",
        "/etc/renku-notebooks/server_options/server_options.json",
    )
    if os.getenv("TELEPRESENCE_ROOT") is not None:
        server_options_file = os.path.join(
            os.getenv("TELEPRESENCE_ROOT"),
            server_options_file.lstrip("/"),
        )
    with open(server_options_file) as f:
        server_options = json.load(f)

    return server_options


def read_server_options_defaults():
    server_options_file = os.getenv(
        "NOTEBOOKS_SERVER_OPTIONS_DEFAULTS_PATH",
        "/etc/renku-notebooks/server_options/server_defaults.json",
    )
    if os.getenv("TELEPRESENCE_ROOT") is not None:
        server_options_file = os.path.join(
            os.getenv("TELEPRESENCE_ROOT"),
            server_options_file.lstrip("/"),
        )
    with open(server_options_file) as f:
        server_options = json.load(f)

    return server_options


def flatten_error_messages(messages, message_ind=0, skip_keys=["json", "_schema"]):
    """
    Takes a list composed of (key, value) tuples
    and unnests all values until no dictionaries are left.
    The unnested dictionary keys are collected and concatenated with '.' notation.
    If a string, integer or anything else other than dictionary is found as a value
    then this is converted to a string and the unnesting for that value stops.
    If any keys are encountered that match the skip_keys list then their values are
    still unnested and included in the final output values but the keys are not merged
    into the keys of the final output.
    """
    if len(messages) == 0:
        return messages
    key, message = messages[message_ind]
    if type(message) is dict:
        key1 = "" if key in skip_keys else f"{key}."
        if message_ind == len(messages) - 1:
            return flatten_error_messages(
                [
                    *messages[:message_ind],
                    *[
                        (
                            key1 + str(i[0]) if i[0] not in skip_keys else key,
                            i[1],
                        )
                        for i in message.items()
                    ],
                ],
                message_ind,
            )
        else:
            return flatten_error_messages(
                [
                    *messages[:message_ind],
                    *[
                        (
                            key1 + str(i[0]) if i[0] not in skip_keys else key,
                            i[1],
                        )
                        for i in message.items()
                    ],
                    *messages[message_ind + 1 :],
                ],
                message_ind,
            )
    elif type(message) is list:
        if message_ind == len(messages) - 1:
            return flatten_error_messages(
                [
                    *messages[:message_ind],
                    (key, "\n".join(map(lambda x: str(x), message))),
                ],
                message_ind,
            )
        else:
            return flatten_error_messages(
                [
                    *messages[:message_ind],
                    (key, "\n".join(map(lambda x: str(x), message))),
                    *messages[message_ind + 1 :],
                ],
                message_ind,
            )
    elif (
        type(message) is not dict
        and type(message) is not list
        and message_ind == len(messages) - 1
    ):
        return messages
    else:
        return flatten_error_messages(messages, message_ind + 1)
