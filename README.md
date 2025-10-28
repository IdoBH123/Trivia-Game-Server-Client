# 🧠 Trivia-Game-Server-Client
A real-time multiplayer trivia game built in Python using custom socket communication.

# 🎯 Overview

Trivia-Game-Server-Client is a Python-based network trivia system with a dedicated server and interactive clients.
Users can log in, receive random questions (from a file or the web), answer them in real time, and earn points.

The server manages:

- 🔑 Login sessions
- 🎲 Question distribution
- 🧮 Scoring and data persistence
- ⚠️ Error handling and session cleanup

All communication uses a custom TCP protocol defined in chatlib.py.

# 🌍 Web-Based Question Loading

The project supports loading 50 random trivia questions from the Open Trivia Database API:
https://opentdb.com/api.php?amount=50&type=multiple

Questions are automatically converted to the server’s internal dictionary format and randomly assigned to each connected user.

# ⚙️ Features

- ✅ Persistent user accounts (stored in users.txt)
- ✅ Option to load local questions from questions.txt
- ✅ Dynamic question loading (via API or local file)
- ✅ Scoring system (+5 points for correct answers)
- ✅ Question tracking per user (prevents repeats)
- ✅ Custom TCP message protocol (human-readable)
- ✅ Robust error handling for invalid messages and disconnects

# 🧩 Architecture

The system includes three main components:
- 🖥 server.py – Handles user connections, authentication, question logic, and scoring.
- 💬 client.py – Connects to the server, displays questions, and sends answers.
- 📜 chatlib.py – Defines the communication protocol and message structure between client and server.



