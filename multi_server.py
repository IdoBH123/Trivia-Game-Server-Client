import socket
import chatlib
import random
import select
import json
import requests
import html


# ---------------- GLOBALS ----------------
users = {}                # username -> {password, score, questions_asked}
questions = {}            # question_number -> {question, answers, correct}
logged_users = {}         # client_addr -> username
messages_to_send = []

ERROR_MSG = "Error! "
SERVER_PORT = 5678
SERVER_IP = "127.0.0.1"

# ---------------- Data Loaders ----------------

def load_questions_from_web():
    """
    Loads 50 multiple-choice questions from the Open Trivia DB API into the global 'questions' dictionary.
    Description:
        Fetches 50 random questions from the Open Trivia Database API and stores them
        in the same format as the local load_questions() function.
    Returns:
        True if successfully loaded, otherwise False.
    """
    global questions
    questions = {}

    try:
        response = requests.get("https://opentdb.com/api.php?amount=50&type=multiple")
        data = response.json()

        if data.get("response_code") != 0:
            print("[SERVER] Failed to load questions from web API.")
            return False

        for idx, item in enumerate(data["results"], start=1):
            question_text = html.unescape(item["question"])
            answers = [html.unescape(ans) for ans in item["incorrect_answers"]]
            correct_answer = html.unescape(item["correct_answer"])
            answers.append(correct_answer)
            random.shuffle(answers)
            correct_index = answers.index(correct_answer) + 1

            questions[idx] = {
                "question": question_text,
                "answers": answers,
                "correct": correct_index
            }

        print(f"[SERVER] Loaded {len(questions)} questions from the web.")
        return True

    except Exception as e:
        print(f"[SERVER] Error loading questions from web: {e}")
        return False

#
# def load_questions():
#     """
#         Loads trivia questions from 'questions.txt' into the global 'questions' dictionary.
#         Each line format:
#           Question, "Answer1", "Answer2", "Answer3", "Answer4", "CorrectAnswer"
#         Skips invalid lines and prints the total number of loaded questions.
#     """
#     global questions
#     questions = {}
#
#     try:
#         with open("questions.txt", "r", encoding="utf-8") as f:
#             lines = f.readlines()
#         for idx, line in enumerate(lines, start=1):
#             parts = [p.strip().strip('"') for p in line.strip().split(",")]
#             if len(parts) != 6:
#                 print(f"[SERVER] Skipping invalid line in questions.txt: {line}")
#                 continue
#             question_text = parts[0]
#             answers = parts[1:5]
#             correct = parts[5]
#             questions[idx] = {
#                 "question": question_text,
#                 "answers": answers,
#                 "correct": correct
#             }
#         print(f"[SERVER] Loaded {len(questions)} questions.")
#     except FileNotFoundError:
#         print("[SERVER] questions.txt not found. No questions loaded.")


def load_user_database():
    """
    Loads users from file users.txt
    Format: username,password,score,questions_asked
    """
    global users
    users = {}
    try:
        with open("users.txt", "r") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) < 3:
                    print(f"[SERVER] Warning: invalid line in users.txt: {line}")
                    continue
                username = parts[0].strip()
                password = parts[1].strip()
                score = int(parts[2].strip())
                questions_asked = []
                if len(parts) > 3 and parts[3].strip():
                    questions_asked = [int(q) for q in parts[3].strip().split()]
                users[username] = {
                    "password": password,
                    "score": score,
                    "questions_asked": questions_asked  # total asked counts
                }
        print(f"[SERVER] Loaded {len(users)} users from users.txt")
    except FileNotFoundError:
        print("[SERVER] users.txt not found. Creating default users.")
        users = {
            "test": {"password": "test", "score": 0, "questions_asked": []},
            "yossi": {"password": "123", "score": 50, "questions_asked": []},
            "master": {"password": "master", "score": 200, "questions_asked": []}
        }


def save_user_database():
    """
        Saves all user data from the global 'users' dictionary into 'users.txt'.
        Each line format:
          username,password,score,question1 question2 question3 ...

        Overwrites the file on each save and prints the total users saved.
        """
    global users
    try:
        with open("users.txt", "w") as file:
            for username, udata in users.items():
                q_asked_str = " ".join(str(q) for q in udata.get("questions_asked", []))
                line = f"{username},{udata['password']},{udata['score']},{q_asked_str}\n"
                file.write(line)
        print(f"[SERVER] Saved {len(users)} users to users.txt")
        return True
    except Exception as e:
        print(f"[SERVER] Error saving users: {e}")
        return False


# ---------------- Messaging ----------------

def build_and_send_message(conn, code, data):
    """
        Builds a new message using chatlib and adds it to the global outgoing message list.
        Instead of sending immediately, it queues the message for later sending.
    """
    global messages_to_send
    try:
        full_msg = chatlib.build_message(code, data)
        messages_to_send.append((conn, full_msg))
        return True
    except Exception as e:
        print(f"[SERVER] Error building message: {e}")
        return False


def recv_message_and_parse(conn):
    """
        Receives a new message from given socket,
        then parses the message using chatlib.
        Returns: cmd (str), data (str), or ERROR_RETURN on failure.
    """
    try:
        full_msg = conn.recv(chatlib.MAX_MSG_LENGTH).decode()
        if not full_msg:
            return None, None
        cmd, data = chatlib.parse_message(full_msg)
        return cmd, data
    except Exception as e:
        print(f"[SERVER] Error receiving/parsing message: {e}")
        return None, None


def setup_socket():
    """
        Creates new listening socket and returns it
        Recieves: -
        Returns: the socket object
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((SERVER_IP, SERVER_PORT))
        s.listen(5)
        return s
    except Exception as e:
        print(f"[SERVER] Socket setup failed: {e}")
        return None


# ---------------- Handlers ----------------

def handle_login_message(conn, data):
    """
        Gets socket and message data of login message. Checks user and password.
        If not valid - sends ERROR. If valid - sends LOGIN_OK and adds user to logged_users.
        Receives: socket, message data
        Returns: None (sends answer to client)
    """
    global users, logged_users

    fields = chatlib.split_data(data, 2)
    if not fields:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], "Invalid login data")
        return

    username, password = fields
    if username not in users:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], f"User '{username}' does not exist")
        return
    if users[username]['password'] != password:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], "Incorrect password")
        return

    logged_users[conn.getpeername()] = username
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER['login_ok_msg'], f"Welcome {username}!")
    print(f"[SERVER] User '{username}' logged in successfully")


def handle_logout_message(conn):
    """
        Removes user from logged_users dictionary and saves their session data.
        Does NOT close the connection - that's handled by the caller.
        Receives: socket
        Returns: None
    """
    global logged_users
    try:
        client_addr = conn.getpeername()
    except:
        return
    if client_addr in logged_users:
        username = logged_users[client_addr]
        del logged_users[client_addr]
        save_user_database()
        print(f"[SERVER] User '{username}' logged out.")


def handle_getscore_message(conn, username):
    """
        Sends the score of the given user to the client.
        Receives: client socket, username
        Returns: None (sends answer to client)
    """
    if username not in users:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], f"User '{username}' does not exist")
        return
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER['yourscore_msg'], str(users[username]['score']))


def handle_highscore_message(conn):
    """
        Sends the highscore list to the client.
        Receives: client socket
        Returns: None (sends answer to client)
    """
    sorted_users = sorted(users.items(), key=lambda item: item[1]['score'], reverse=True)
    highscore_str = "\n".join(f"{u}:{ud['score']}" for u, ud in sorted_users)
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER['highscore_msg'], highscore_str)


def handle_logged_message(conn):
    """
        Sends the list of currently logged-in users to the client.
        Receives: client socket
        Returns: None (sends answer to client)
    """
    usernames = list(logged_users.values())
    logged_str = chatlib.join_data(usernames)
    build_and_send_message(conn, chatlib.PROTOCOL_SERVER['logged_msg'], logged_str)


def create_random_question(username):
    """
    Description:
        Selects a random question that the given user has not yet been asked.
        If all questions have been asked, returns None.
    Receives:
        username (str) – the name of the logged-in user requesting a new question.
    Returns:
        tuple (str, int) – formatted question string for the protocol and its question number,
                           or None if no available question remains.
    """
    if not questions:
        return None

    asked = set(users[username].get("questions_asked", []))
    available_qs = [q_num for q_num in questions.keys() if q_num not in asked]
    if not available_qs:
        return None

    q_num = random.choice(available_qs)
    q_data = questions[q_num]
    answers = "#".join(q_data["answers"])
    return f"{q_num}#{q_data['question']}#{answers}", q_num


def handle_question_message(conn, username):
    """
        Description:
            Handles a user's request for a new trivia question.
            Retrieves a random question not yet asked to the user.
            If no questions remain, sends an error message instead.
        Receives:
            conn (socket) – the client’s socket connection.
            username (str) – the name of the logged-in user requesting a question.
        Returns: None
        """
    result = create_random_question(username)
    if result:
        question_str, q_num = result
        users[username]["questions_asked"].append(q_num)  # save question to history
        save_user_database()
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['question_msg'], question_str)
        print(f"[SERVER] Sent question {q_num} to {username}")
    else:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], "No more questions available")


def handle_answer_message(conn, username, data):
    """
        Check user's answer and update score if correct.
        Receives: conn (socket), username (str), data (str with 'q_num#ans')
        Returns: Sends response to client (correct or wrong)
    """
    global users
    try:
        q_num_str, ans_str = data.split("#")
        q_num = int(q_num_str)
        user_ans = int(ans_str)
    except:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], "Invalid answer format")
        return

    if q_num not in questions:
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], "Question does not exist")
        return

    correct_ans = int(questions[q_num]['correct'])
    if user_ans == correct_ans:
        users[username]['score'] += 5
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['correct_msg'], "5")
    else:
        correct_text = questions[q_num]['answers'][correct_ans-1]
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['wrong_msg'], f"{correct_ans},{correct_text}")


def handle_client_message(conn, cmd, data):
    """
    Gets message code and data and calls the right function to handle command
    Receives: socket, message code and data
    Returns: True if client should stay connected, False if should disconnect
    """
    global logged_users

    try:
        client_addr = conn.getpeername()
    except:
        return False

    is_logged_in = client_addr in logged_users

    # If client is not logged in, only LOGIN is allowed
    if not is_logged_in:
        if cmd != chatlib.PROTOCOL_CLIENT['login_msg']:
            build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], "You must login first")
            return True
        handle_login_message(conn, data)
        return True

    # Client is logged in
    username = logged_users[client_addr]

    if cmd == chatlib.PROTOCOL_CLIENT['logout_msg']:
        handle_logout_message(conn)
        return False  # Signal to disconnect this client

    elif cmd == chatlib.PROTOCOL_CLIENT['getscore_msg']:
        handle_getscore_message(conn, username)

    elif cmd == chatlib.PROTOCOL_CLIENT['gethighscore_msg']:
        handle_highscore_message(conn)

    elif cmd == chatlib.PROTOCOL_CLIENT['getlogged_msg']:
        handle_logged_message(conn)

    elif cmd == chatlib.PROTOCOL_CLIENT['getquestion_msg']:
        handle_question_message(conn, username)

    elif cmd == chatlib.PROTOCOL_CLIENT['sendanswer_msg']:
        handle_answer_message(conn, username, data)

    else:
        print(f"[SERVER] Unknown command: {cmd}")
        build_and_send_message(conn, chatlib.PROTOCOL_SERVER['error_msg'], "Unsupported command")

    return True  # Keep connection alive


def main():
    """
    Main server function.
    Prepares the server socket, listens for clients, and handles messages in a loop.
    Handles controlled LOGOUT and unexpected client disconnects (empty messages).
    """
    global users, questions, messages_to_send

    print("Welcome to Trivia Server!")

    # Load initial data
    load_user_database()
    load_questions_from_web()

    ## for local questions
    # load_questions()

    # Setup server socket
    server_socket = setup_socket()
    if not server_socket:
        print("[SERVER] Failed to set up server socket. Exiting.")
        return

    # Local list of active sockets
    client_sockets = [server_socket]

    print(f"[SERVER] Server is up and listening on {SERVER_IP}:{SERVER_PORT}")

    try:
        while True:
            try:
                # Wait for sockets ready to read
                read_sockets, _, _ = select.select(client_sockets, [], [], 0.5)

                for sock in read_sockets:
                    # New client connection
                    if sock == server_socket:
                        client_conn, client_addr = server_socket.accept()
                        print(f"[SERVER] New connection from {client_addr}")
                        client_sockets.append(client_conn)
                        continue

                    # Existing client
                    try:
                        client_addr = sock.getpeername()
                    except:
                        if sock in client_sockets:
                            client_sockets.remove(sock)
                        continue

                    try:
                        cmd, data = recv_message_and_parse(sock)
                        if cmd is None:
                            # Client disconnected
                            print(f"[SERVER] Client {client_addr} disconnected")
                            handle_logout_message(sock)
                            if sock in client_sockets:
                                client_sockets.remove(sock)
                            sock.close()
                            continue

                        # Handle client message
                        alive = handle_client_message(sock, cmd, data)
                        if not alive:
                            if sock in client_sockets:
                                client_sockets.remove(sock)
                            sock.close()
                            continue

                    except ConnectionResetError:
                        print(f"[SERVER] Connection reset by {client_addr}")
                        handle_logout_message(sock)
                        if sock in client_sockets:
                            client_sockets.remove(sock)
                        try: sock.close()
                        except: pass
                        continue

                    except Exception as e:
                        print(f"[SERVER] Error handling client {client_addr}: {e}")
                        try:
                            build_and_send_message(sock, chatlib.PROTOCOL_SERVER['error_msg'], "Server error occurred")
                        except: pass
                        continue

                # Send queued messages
                for msg_tuple in messages_to_send[:]:
                    conn, msg = msg_tuple
                    try:
                        try:
                            conn.getpeername()  # Check if socket is still valid
                        except:
                            messages_to_send.remove(msg_tuple)
                            continue

                        conn.sendall(msg.encode())
                        messages_to_send.remove(msg_tuple)

                    except Exception as e:
                        print(f"[SERVER] Failed to send message: {e}")
                        messages_to_send.remove(msg_tuple)
                        if conn in client_sockets:
                            handle_logout_message(conn)
                            client_sockets.remove(conn)
                            try: conn.close()
                            except: pass

            except Exception as e:
                print(f"[SERVER] Unexpected error in main loop: {e}")

    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down server...")
        save_user_database()
        for sock in client_sockets:
            try: sock.close()
            except: pass


if __name__ == '__main__':
    main()
