<div align="center">

# J.A.R.V.I.S.

### Just A Rather Very Intelligent System

**Your personal desktop assistant, powered by local AI.**

Talk to your assistant, ask about your inbox, keep track of coursework, and get a daily briefing — from one simple interface.

<br>

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Platforms](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-2ea44f?style=for-the-badge)
![AI](https://img.shields.io/badge/AI-Ollama%20%7C%20Local-7E57C2?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

*Inspired by the idea of having a capable AI assistant right on your computer.*

</div>

---

## ✨ What is J.A.R.V.I.S.?

J.A.R.V.I.S. is a cross-platform personal assistant built in Python. It combines a **local AI model** with optional **voice interaction**, **Gmail**, and **Google Classroom** integration.

Use it to ask general questions, check unread emails, review pending coursework, or get a quick overview of what needs your attention.

The AI runs through [Ollama](https://ollama.com), so your general conversations are handled by a model running on your own machine. Google features are optional and use read-only access.

## 🚀 Features

| Feature | What it does |
|---|---|
| 🧠 **Local AI brain** | Answers general questions using an Ollama model running on your computer |
| 🎙️ **Voice mode** | Accepts microphone input and can speak replies |
| 📧 **Gmail integration** | Checks and lists unread inbox messages |
| 🎓 **Google Classroom** | Shows pending assignments and quizzes, including due-date categories |
| ⚡ **Daily briefing** | Brings email and coursework information together |
| 📊 **System status** | Checks the local AI, configured model, Google login, and voice output |
| 🪟 **Cross-platform setup** | Includes setup and launch helpers for Windows and Linux |
| 🔐 **Read-only Google access** | Uses read-only Google permissions; it cannot send, edit, or delete your data |

## 🖥️ Platform support

J.A.R.V.I.S. is designed for:

- **Windows**
- **Linux**, with setup support for Fedora, Debian/Ubuntu, and Arch-based systems

The automated test workflow covers Windows and Ubuntu runners, with an additional Fedora container check. Hardware-dependent features such as microphones, speakers, and Google sign-in should still be tested on the machine where you plan to use J.A.R.V.I.S.

## 📦 Requirements

Before installing, make sure you have:

- Python **3.9 or newer** (Python 3.10+ is recommended)
- An internet connection for installation, Google services, and online speech recognition
- [Ollama](https://ollama.com) for local AI conversations
- A microphone for voice input (optional)
- Speakers or headphones for spoken replies (optional)
- Google Cloud OAuth credentials if you want Gmail and Classroom features

> **Good to know:** The local AI model runs on your computer after it has been downloaded. Gmail, Classroom, and the current speech-recognition input require an internet connection.

## 🛠️ Installation

### 1. Get the project

Download the repository from GitHub, or clone it:

```bash
git clone https://github.com/abdulnafey543/J.A.R.V.I.S.git

```


### 2. Run the setup

**Windows — PowerShell**

```powershell
python setup.py
```

**Fedora**

```bash
sudo dnf install python3
python3 setup.py
```

**Debian / Ubuntu**

```bash
sudo apt install python3 python3-venv
python3 setup.py
```

**Arch Linux**

```bash
sudo pacman -S python
python3 setup.py
```

The setup script creates a project-specific `.venv`, installs the Python dependencies, checks or installs supported Linux voice libraries, and helps prepare Ollama and the configured model.

### 3. Connect Google (optional)

To use Gmail and Google Classroom:

1. Follow **[Google setup instructions](docs/GOOGLE_SETUP.md)**.
2. Place your downloaded OAuth client file at `credentials/client_secret.json`.
3. Run the Google login helper:

   **Windows**
   ```powershell
   .venv\Scripts\python.exe setup_google.py
   ```

   **Linux**
   ```bash
   .venv/bin/python setup_google.py
   ```

Google setup is optional. You can still use the local AI without connecting a Google account.

### 4. Check your installation

**Windows**
```powershell
python run.py --check
```

**Linux**
```bash
python3 run.py --check
```

### 5. Launch J.A.R.V.I.S.

**Text mode — Windows**
```powershell
python run.py
```

**Text mode — Linux**
```bash
python3 run.py
```

**Voice mode — Windows**
```powershell
python run.py --voice
```

**Voice mode — Linux**
```bash
python3 run.py --voice
```

The first setup may take a little time while packages and the AI model are prepared.

## 💬 What can I ask?

Try these example commands:

| Say or type | J.A.R.V.I.S. responds with |
|---|---|
| `Hello` | A quick daily briefing |
| `Any new emails?` | Unread inbox messages |
| `What homework is due?` | Pending Google Classroom work |
| `Quizzes?` | Pending quizzes |
| `Briefing` | A combined email and coursework overview |
| `What should I do first today?` | An AI-generated priority suggestion using available email and coursework context |
| `Explain pointers in C++` | A response from your local AI model |
| `Status` | A quick check of configured services |
| `Help` | Available built-in commands |
| `Quit` | Closes J.A.R.V.I.S. |

Anything that does not match a built-in command is sent to the local AI model.

## ⚙️ Configuration

J.A.R.V.I.S. uses **Qwen 2.5 3B** by default through Ollama.

You can choose another model by setting `JARVIS_MODEL`.

**Windows PowerShell**
```powershell
$env:JARVIS_MODEL = "llama3.2:3b"
python run.py
```

**Linux**
```bash
JARVIS_MODEL=llama3.2:3b python3 run.py
```

For additional troubleshooting output, set `JARVIS_DEBUG=1`.

**Windows PowerShell**
```powershell
$env:JARVIS_DEBUG = "1"
python run.py
```

**Linux**
```bash
JARVIS_DEBUG=1 python3 run.py
```

## 🧩 How it works

```text
                         ┌────────────────────┐
                         │      You           │
                         │  Text or voice     │
                         └─────────┬──────────┘
                                   │
                         ┌─────────▼──────────┐
                         │      main.py       │
                         │ Conversation loop  │
                         └─────────┬──────────┘
                                   │
                         ┌─────────▼──────────┐
                         │    commands.py     │
                         │  Command routing   │
                         └───┬─────┬─────┬────┘
                             │     │     │
              ┌──────────────┘     │     └──────────────┐
              │                    │                    │
      ┌───────▼────────┐   ┌───────▼────────┐   ┌───────▼────────┐
      │    brain.py    │   │    gmail.py    │   │  classroom.py  │
      │ Ollama / AI    │   │ Unread emails  │   │ Pending work   │
      └────────────────┘   └────────────────┘   └────────────────┘
              │                    │                    │
              └────────────────────┴────────────────────┘
                                   │
                         ┌─────────▼──────────┐
                         │      voice.py      │
                         │ Speech input/output│
                         └────────────────────┘

       Supporting modules: auth.py, setup.py, run.py,
       check.py and platform_utils.py
```

### Project structure

```text
J.A.R.V.I.S/
├── .github/workflows/   # Automated tests (GitHub Actions)
├── credentials/         # Local Google credentials (not committed)
├── docs/                # Setup guides and screenshot notes
├── tests/               # Automated unit tests
├── auth.py              # Google OAuth authentication
├── brain.py             # Ollama connection and AI conversation
├── classroom.py         # Google Classroom integration
├── commands.py          # Built-in command recognition
├── gmail.py             # Gmail integration
├── main.py              # Main assistant loop
├── platform_utils.py    # Windows/Linux compatibility helpers
├── setup.py             # Installation and environment setup
├── setup_google.py      # Google account connection
├── run.py               # Application launcher
└── voice.py              # Speech input and output
```

## 🔒 Privacy and security

Your data matters. Here is how J.A.R.V.I.S. handles it:

- **Local AI:** General AI conversations are processed by your local Ollama model.
- **Google permissions:** Gmail and Classroom access is read-only. J.A.R.V.I.S. cannot send emails or modify or delete Google data.
- **Voice input:** The current speech-recognition input uses Google's online speech recognition service. Microphone audio is sent to Google for transcription.
- **Voice output:** Speech output is generated locally through the available speech engine.
- **Credentials:** OAuth secrets and tokens belong in `credentials/` and must never be committed to Git.

Read **[SECURITY.md](SECURITY.md)** before publishing or sharing your setup. For Google configuration details, see **[docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md)**.

## 🧪 Tests

Run the automated test suite from the project directory:

```bash
python -m unittest discover -s tests -t . -v
```

The tests cover command routing, Gmail parsing and pagination, Classroom work and due-date handling, voice failure recovery, AI error handling, and platform-specific path handling.

GitHub Actions runs the test suite on Windows and Ubuntu across multiple Python versions, plus a Fedora container check.

> Automated tests do not replace testing on your own hardware. Microphone devices, speakers, Ollama model downloads, and Google OAuth depend on your local environment.

## 🗺️ Roadmap

Ideas for future versions:

- [ ] Offline speech recognition
- [ ] Wake-word activation
- [ ] Google Calendar integration (read-only)
- [ ] Streaming AI responses
- [ ] Optional desktop notifications for upcoming assignments
- [ ] Music playback controls

These are planned ideas, not features currently included in this release.

## 🤝 Contributing

Suggestions, bug reports, and improvements are welcome.

Please read **[CONTRIBUTING.md](CONTRIBUTING.md)** before submitting changes. When reporting a problem, include your operating system, Python version, and the relevant error message — but never include passwords, OAuth tokens, or credential files.

## 📄 License

J.A.R.V.I.S. is released under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with Python, Ollama, and a little inspiration from the future.**

*J.A.R.V.I.S. — Your computer, a little more intelligent.*

</div>

