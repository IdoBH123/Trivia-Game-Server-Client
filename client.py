import socket
import chatlib

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5678
ERROR_RETURN = None


# ===================== Network helpers =====================
def build_and_send_message(conn, code, data):
    """
    Builds a new message using chatlib and sends it to the server.
    """
    try:
        full_msg = chatlib.build_message(code, data)
        if full_msg is None:
            print("Error: Failed to build message")
            return False
        print("[CLIENT] Sending:", repr(full_msg))
        conn.sendall(full_msg.encode())
        return True
    except Exception as e:
        print("Error building or sending message:", e)
        return False


def recv_message_and_parse(conn):
    """
    Receives a new message from given socket,
    then parses the message using chatlib.
    Returns: cmd (str), data (str), or ERROR_RETURN on failure.
    """
    try:
        # Use larger buffer to match server's max message size
        full_msg = conn.recv(chatlib.MAX_MSG_LENGTH).decode()
        if not full_msg:
            return chatlib.ERROR_RETURN, chatlib.ERROR_RETURN

        print("[CLIENT] Received:", repr(full_msg))
        cmd, data = chatlib.parse_message(full_msg)
        return cmd, data
    except Exception as e:
        print("Error receiving or parsing message:", e)
        return chatlib.ERROR_RETURN, chatlib.ERROR_RETURN


def build_send_recv_parse(conn, cmd, data):
    """
    Builds, sends, then waits for a response message.
    Returns: response_cmd, response_data
    """
    if not build_and_send_message(conn, cmd, data):
        return chatlib.ERROR_RETURN, chatlib.ERROR_RETURN

    response_cmd, response_data = recv_message_and_parse(conn)
    if response_cmd == chatlib.ERROR_RETURN:
        print("Error: failed to communicate with server")
    return response_cmd, response_data


# ===================== Game logic functions =====================
def connect():
    """
    Establishes connection to the server.
    Returns: socket object or None on failure
    """
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_IP, SERVER_PORT))
        print("Connected to server.")
        return client_socket
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        return None


def login(conn):
    """
    Prompts user for credentials and attempts login.
    Returns: True if login successful, False otherwise
    """
    while True:
        username = input("Please enter username: ").strip()
        password = input("Please enter password: ").strip()

        if not username or not password:
            print("Username and password cannot be empty!")
            continue

        data = chatlib.join_data([username, password])
        cmd, msg = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT['login_msg'], data)

        if cmd == chatlib.PROTOCOL_SERVER['login_ok_msg']:
            print("Login successful!")
            return True
        elif cmd == chatlib.ERROR_RETURN:
            print("Connection error. Please try again.")
            retry = input("Try again? (y/n): ").lower()
            if retry != 'y':
                return False
        else:
            print("Login failed:", msg)
            retry = input("Try again? (y/n): ").lower()
            if retry != 'y':
                return False


def get_score(conn):
    """
    Requests and displays the current user's score.
    """
    cmd, msg = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT['getscore_msg'], "")
    if cmd == chatlib.PROTOCOL_SERVER['yourscore_msg']:
        print(f"\n{'=' * 30}")
        print(f"Your current score: {msg}")
        print(f"{'=' * 30}")
    else:
        print("Failed to get score:", msg)


def get_highscore(conn):
    """
    Requests and displays the high scores table.
    """
    cmd, msg = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT['gethighscore_msg'], "")
    if cmd == chatlib.PROTOCOL_SERVER['highscore_msg']:
        print(f"\n{'=' * 30}")
        print("HIGH SCORES")
        print(f"{'=' * 30}")
        print(msg)
        print(f"{'=' * 30}")
    else:
        print("Failed to get high scores:", msg)


def get_logged_users(conn):
    """
    Requests and displays currently logged-in users.
    """
    cmd, msg = build_send_recv_parse(conn, chatlib.PROTOCOL_CLIENT['getlogged_msg'], "")
    if cmd == chatlib.PROTOCOL_SERVER['logged_msg']:
        if msg:
            users_list = msg.split('#')
            print(f"\n{'=' * 30}")
            print(f"Currently logged in ({len(users_list)} user(s)):")
            print(f"{'=' * 30}")
            for user in users_list:
                print(f"  - {user}")
            print(f"{'=' * 30}")
        else:
            print("No users currently logged in.")
    else:
        print("Failed to get logged users:", msg)


def logout(conn):
    """
    Sends logout message and closes connection.
    """
    try:
        build_and_send_message(conn, chatlib.PROTOCOL_CLIENT['logout_msg'], "")
        conn.close()
        print("Logged out successfully. Connection closed.")
    except Exception as e:
        print(f"Error during logout: {e}")


def play_question(conn):
    """
    Requests a question from server, displays it, gets user's answer,
    and shows the result.
    """
    # Step 1: Request a question from the server
    cmd, data = build_send_recv_parse(
        conn,
        chatlib.PROTOCOL_CLIENT['getquestion_msg'],
        ""
    )

    if cmd == chatlib.ERROR_RETURN:
        print("Error: Failed to receive question from server")
        return

    # Step 2: Handle case where no more questions remain
    if cmd == chatlib.PROTOCOL_SERVER['noquestions_msg']:
        print("\n" + "=" * 40)
        print("No more questions available!")
        print("=" * 40)
        return

    # Step 3: Check if we got an error
    if cmd == chatlib.PROTOCOL_SERVER['error_msg']:
        print(f"Error from server: {data}")
        return

    # Step 4: Verify we got a question
    if cmd != chatlib.PROTOCOL_SERVER['question_msg']:
        print(f"Unexpected response from server: {cmd}")
        return

    # Step 5: Parse the question data
    # Format: question_id#question#answer1#answer2#answer3#answer4
    question_fields = chatlib.split_data(data, 6)
    if not question_fields:
        print("Error: Invalid question format from server")
        return

    question_id, question_text, ans1, ans2, ans3, ans4 = question_fields

    # Step 6: Display the question to the user
    print("\n" + "=" * 50)
    print("NEW QUESTION")
    print("=" * 50)
    print(f"Q: {question_text}")
    print(f"  1. {ans1}")
    print(f"  2. {ans2}")
    print(f"  3. {ans3}")
    print(f"  4. {ans4}")
    print("=" * 50)

    # Step 7: Get user's answer with validation
    while True:
        user_answer = input("Your answer (1-4): ").strip()
        if user_answer in ['1', '2', '3', '4']:
            break
        print("Invalid input! Please enter a number between 1 and 4.")

    # Step 8: Send the answer to the server
    # Format: question_id#answer_choice
    answer_data = chatlib.join_data([question_id, user_answer])
    cmd, data = build_send_recv_parse(
        conn,
        chatlib.PROTOCOL_CLIENT['sendanswer_msg'],
        answer_data
    )

    if cmd == chatlib.ERROR_RETURN:
        print("Error: Failed to receive result from server")
        return

    # Step 9: Display the result
    print("\n" + "=" * 50)
    if cmd == chatlib.PROTOCOL_SERVER['correct_msg']:
        print("✅ CORRECT ANSWER!")
        print(f"You earned {data} points!" if data else "Great job!")
    elif cmd == chatlib.PROTOCOL_SERVER['wrong_msg']:
        print("❌ WRONG ANSWER")
        print(f"The correct answer is #{data}")
    else:
        print(f"Unexpected response from server: {cmd} - {data}")
    print("=" * 50)



# ===================== Main menu =====================
def main():
    print("=" * 40)
    print("Welcome to the Trivia Game Client!")
    print("=" * 40)

    conn = connect()
    if conn is None:
        print("Cannot connect to server. Exiting.")
        return

    try:
        if not login(conn):
            print("Login cancelled or failed. Exiting.")
            return

        while True:
            print("\n" + "=" * 40)
            print("MAIN MENU")
            print("=" * 40)
            print("1. Get my score")
            print("2. Get high scores")
            print("3. Play a question")
            print("4. Get logged users")
            print("5. Logout")
            print("=" * 40)
            choice = input("Enter your choice (1-5): ").strip()

            if choice == '1':
                get_score(conn)
            elif choice == '2':
                get_highscore(conn)
            elif choice == '3':
                play_question(conn)
            elif choice == '4':
                get_logged_users(conn)
            elif choice == '5':
                logout(conn)
                return  # Exit cleanly
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Logging out...")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        # Always try to clean up the connection
        try:
            if conn.fileno() != -1:  # Check if socket is still valid
                logout(conn)
        except:
            pass  # Socket already closed, ignore

if __name__ == "__main__":
    main()