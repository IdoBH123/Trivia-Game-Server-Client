# Protocol Constants

CMD_FIELD_LENGTH = 16  # Exact length of cmd field (in bytes)
LENGTH_FIELD_LENGTH = 4  # Exact length of length field (in bytes)
MAX_DATA_LENGTH = 10 ** LENGTH_FIELD_LENGTH - 1  # Max size of data field according to protocol
MSG_HEADER_LENGTH = CMD_FIELD_LENGTH + 1 + LENGTH_FIELD_LENGTH + 1  # Exact size of header (CMD+LENGTH fields)
MAX_MSG_LENGTH = MSG_HEADER_LENGTH + MAX_DATA_LENGTH  # Max size of total message
DELIMITER = "|"  # Delimiter character in protocol
DATA_DELIMITER = "#"  # Delimiter in the data part of the message

# Protocol Messages
# In this dictionary we will have all the client and server command names

# ----------------- Protocol Constants -----------------
PROTOCOL_CLIENT = {
    "login_msg": "LOGIN",
    "logout_msg": "LOGOUT",
    "getscore_msg": "MY_SCORE",
    "getlogged_msg": "LOGGED",
    "gethighscore_msg": "HIGHSCORE",
    "getquestion_msg": "GET_QUESTION",
    "sendanswer_msg": "SEND_ANSWER"
}

PROTOCOL_SERVER = {
    "login_ok_msg": "LOGIN_OK",
    "login_failed_msg": "ERROR",
    "yourscore_msg": "YOUR_SCORE",
    "highscore_msg": "ALL_SCORE",
    "logged_msg": "LOGGED_ANSWER",
    "correct_msg": "CORRECT_ANSWER",
    "wrong_msg": "WRONG_ANSWER",
    "question_msg": "YOUR_QUESTION",
    "error_msg": "ERROR",
    "noquestions_msg": "NO_QUESTIONS"
}

# Other constants

ERROR_RETURN = None  # What is returned in case of an error


def build_message(cmd, data):
    """
    Gets command name (str) and data field (str) and creates a valid protocol message
    Returns: str, or None if error occurred
    """
    if not isinstance(cmd, str) or not isinstance(data, str):
        return None
    if len(cmd) > CMD_FIELD_LENGTH or len(data) > MAX_DATA_LENGTH:
        return None
    if DELIMITER in cmd or DATA_DELIMITER in cmd:
        return None

    # Pad command to exactly CMD_FIELD_LENGTH characters
    padded_cmd = cmd.ljust(CMD_FIELD_LENGTH)

    # Format length as 4-digit zero-padded string
    length = len(data)
    length_str = str(length).zfill(LENGTH_FIELD_LENGTH)

    # Build the full message
    full_msg = f"{padded_cmd}{DELIMITER}{length_str}{DELIMITER}{data}"
    return full_msg


def parse_message(message):
    """
    Parses protocol message and returns command name and data field
    Returns: cmd (str), data (str). If some error occurred, returns None, None
    """
    if not isinstance(message, str):
        return None, None

    # Check minimum length
    if len(message) < MSG_HEADER_LENGTH:
        return None, None

    # Check delimiters are in correct positions
    if message[CMD_FIELD_LENGTH] != DELIMITER:
        return None, None
    if message[CMD_FIELD_LENGTH + 1 + LENGTH_FIELD_LENGTH] != DELIMITER:
        return None, None

    # Extract command (strip whitespace padding)
    cmd = message[:CMD_FIELD_LENGTH].strip()

    # Extract length field
    length_str = message[CMD_FIELD_LENGTH + 1:CMD_FIELD_LENGTH + 1 + LENGTH_FIELD_LENGTH]

    # Validate length is a number
    if not length_str.isdigit():
        return None, None

    msg_length = int(length_str)

    # Extract data
    data_start = MSG_HEADER_LENGTH
    data = message[data_start:data_start + msg_length]

    # Validate data length matches
    if len(data) != msg_length:
        return None, None

    return cmd, data


def split_data(msg, expected_fields):
    """
    Helper method. Gets a string and number of expected fields in it. Splits the string
    using protocol's data field delimiter (#) and validates that there are correct number of fields.
    Returns: list of fields if all ok. If some error occurred, returns None
    """
    if not msg:
        # Handle empty message case
        if expected_fields == 1:
            return [""]
        return None

    fields = msg.split(DATA_DELIMITER)

    if len(fields) == expected_fields:
        return fields

    return None


def join_data(msg_fields):
    """
    Helper method. Gets a list, joins all of its fields into one string divided by the data delimiter.
    Returns: string that looks like cell1#cell2#cell3
    """
    return DATA_DELIMITER.join(msg_fields)



# def main():
#     # print(split_data("username#password", 1))
#     # # ['username', 'password']
#     # print(split_data("user#name#pass#word", 2))
#     # # [None]
#     # print(split_data("username", 2))
#     # # [None]
#     # print(join_data(["username", "password"]))
#     # print(join_data(["question", "ans1", "ans2", "ans3", "ans4", "correct"]))
#     # print(build_message("LOGIN", "aaaa#bbbb"))  # LOGIN#0009|aaaa#bbbb
#     # print(build_message("LOGIN", "aaaabbbb"))  # LOGIN#0008|aaaabbbb
#     print(parse_message("LOGIN|0009|aaaa#bbbb"))  # ('LOGIN', 'aaaa#bbbb')
#     print(parse_message("LOGIN|0009|aaaa#bbbb"))  # ('LOGIN', 'aaaa#bbbb')
#     print(parse_message("LOGIN| $ 9|aaaa#bbbb"))  # (None, None)
#     print(parse_message("LOGIN | z|aaaa"))  # (None, None)
#
# if __name__ == "__main__":
#     main()
