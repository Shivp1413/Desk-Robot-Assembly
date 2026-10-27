import os
import json
import socket
import threading

import requests
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# =========================================================
# DEFAULTS
# =========================================================

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "bonsai-2:2b"

DEFAULT_ROBOT_HOST = "192.168.1.50"   # or "robot1.local"
DEFAULT_ROBOT_PORT = 3361

SYSTEM_PROMPT = """
You are a robot servo intent classifier.

Return ONLY a JSON object:
{"intent":"move_right","size":"small"}

Allowed intents:
move_left, move_right, more, reverse, stop, center,
happy, sad, unclear

Allowed sizes:
tiny, small, medium, large

Rules:
- Turn left => move_left
- Turn right => move_right
- More please / continue => more
- Other way / opposite direction => reverse
- Stop => stop
- Look straight / center / zero position => center
- Happy => happy
- Sad => sad
- Unclear request => unclear

Size rules:
- Tiny / very slightly => tiny
- A little / little bit / slightly => small
- Medium => medium
- A lot / much further => large
- Degrees up to 5 => tiny
- Degrees 6-15 => small
- Degrees 16-35 => medium
- Degrees above 35 => large

These are approximate time categories, NOT accurate angles.
Never output servo commands like R80 or L160.
Never output explanations, markdown, or reasoning.
Return only JSON.
"""

DURATIONS = {
    "tiny": 50,
    "small": 80,
    "medium": 160,
    "large": 300,
}

INTENTS = {
    "move_left", "move_right", "more", "reverse",
    "stop", "center", "happy", "sad", "unclear"
}

# =========================================================
# SETTINGS FILE (same folder as this script)
# =========================================================

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.path.expanduser("~")

SETTINGS_FILE = os.path.join(BASE_DIR, "llm_servo_settings.json")

# =========================================================
# APPLICATION STATE
# =========================================================

history = [{"role": "system", "content": SYSTEM_PROMPT}]
last_direction = None
busy = False

# Persistent UDP socket: stable source port so the ESP32's ACKs
# (sent to the last sender) always come back to us.
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    SOCK.bind(("0.0.0.0", 0))
except OSError:
    pass  # unbound socket still works after first sendto

ack_event = threading.Event()

# =========================================================
# SETTINGS LOAD / SAVE
# =========================================================

def save_settings_file(silent=False):
    """Validate current UI values and write them to disk."""
    try:
        settings = get_settings()
    except Exception as exc:
        if not silent:
            messagebox.showerror("Settings error", str(exc))
        return False

    data = {
        "provider": settings["provider"],
        "url": settings["url"],
        "token": settings["token"],
        "model": settings["model"],
        "think_off": settings["think_off"],
        "robot_host": settings["robot_host"],
        "robot_port": settings["robot_port"],
        "live_send": settings["live_send"],
    }

    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as exc:
        if not silent:
            messagebox.showerror("Save error", "Could not save settings:\n" + str(exc))
        return False

    if not silent:
        settings_status.set("Settings saved to " + SETTINGS_FILE)
    return True


def load_settings_file():
    """Load saved settings into the UI at startup (if the file exists)."""
    if not os.path.exists(SETTINGS_FILE):
        return False

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print("Could not read settings file:", exc)
        return False

    provider_var.set(data.get("provider", "Ollama"))
    url_var.set(data.get("url", OLLAMA_URL))
    token_var.set(data.get("token", ""))
    model_var.set(data.get("model", DEFAULT_MODEL))
    think_var.set(bool(data.get("think_off", True)))
    robot_host_var.set(data.get("robot_host", DEFAULT_ROBOT_HOST))
    robot_port_var.set(str(data.get("robot_port", DEFAULT_ROBOT_PORT)))
    live_var.set(bool(data.get("live_send", False)))

    return True

# =========================================================
# SETTINGS TAB
# =========================================================

def load_settings_into_ui():
    provider_var.set("Ollama")
    url_var.set(OLLAMA_URL)
    token_var.set("")
    model_var.set(DEFAULT_MODEL)
    think_var.set(True)
    robot_host_var.set(DEFAULT_ROBOT_HOST)
    robot_port_var.set(str(DEFAULT_ROBOT_PORT))
    live_var.set(False)
    update_provider_ui()


def update_provider_ui(event=None):
    provider = provider_var.get()

    if provider == "Ollama":
        if not url_var.get().strip():
            url_var.set(OLLAMA_URL)
        token_entry.configure(state="disabled")
        think_check.configure(
            text="Disable thinking (if supported by model)"
        )
    else:
        token_entry.configure(state="normal")
        think_check.configure(
            text="Send think=false (if supported by API)"
        )
        if url_var.get().strip() == OLLAMA_URL:
            url_var.set(
                "https://your-provider.example/v1/chat/completions"
            )


def get_settings():
    provider = provider_var.get()
    url = url_var.get().strip()
    token = token_var.get().strip()
    model = model_var.get().strip()

    if not url or not model:
        raise ValueError("API URL and model name are required.")

    if provider == "Ollama":
        url = url.rstrip("/")
        if not url.endswith("/api/chat"):
            url += "/api/chat"

    host = robot_host_var.get().strip()
    if not host:
        raise ValueError("Robot host/IP is required.")

    try:
        port = int(robot_port_var.get().strip())
    except ValueError:
        raise ValueError("Robot UDP port must be a number.")

    if not (1 <= port <= 65535):
        raise ValueError("Robot UDP port must be 1-65535.")

    return {
        "provider": provider,
        "url": url,
        "token": token,
        "model": model,
        "think_off": think_var.get(),
        "robot_host": host,
        "robot_port": port,
        "live_send": live_var.get(),
    }


def test_connection():
    try:
        settings = get_settings()
    except Exception as exc:
        messagebox.showerror("Settings error", str(exc))
        return

    test_button.configure(state="disabled")
    settings_status.set("Testing LLM connection...")

    threading.Thread(
        target=connection_worker,
        args=(settings,),
        daemon=True
    ).start()


def connection_worker(settings):
    try:
        if settings["provider"] == "Ollama":
            url = settings["url"].replace("/api/chat", "/api/tags")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            names = [m.get("name", "") for m in models]

            if settings["model"] not in names:
                raise ValueError(
                    "Connected to Ollama, but model was not found. "
                    "Available models: " + ", ".join(names)
                )

        else:
            headers = {"Content-Type": "application/json"}
            if settings["token"]:
                headers["Authorization"] = (
                    "Bearer " + settings["token"]
                )

            response = requests.post(
                settings["url"],
                headers=headers,
                json={
                    "model": settings["model"],
                    "messages": [
                        {"role": "user", "content": "Reply with OK"}
                    ],
                    "stream": False,
                    "temperature": 0,
                },
                timeout=30,
            )
            response.raise_for_status()

        root.after(
            0, settings_status.set,
            "LLM connection successful."
        )

    except Exception as exc:
        root.after(
            0, settings_status.set,
            "LLM connection failed: " + str(exc)
        )

    finally:
        root.after(
            0, lambda: test_button.configure(state="normal")
        )


def save_settings():
    if save_settings_file(silent=False):
        notebook.select(command_tab)

# =========================================================
# UDP ROBOT LINK
# =========================================================

def udp_send(text, settings):
    """Send one command line to the robot."""
    SOCK.sendto((text + "\n").encode("utf-8"),
                (settings["robot_host"], settings["robot_port"]))


def udp_listener():
    """Background thread: receive ACK/status lines from the robot."""
    while True:
        try:
            data, addr = SOCK.recvfrom(2048)
        except OSError:
            return

        text = data.decode("utf-8", errors="replace")
        ack_event.set()

        for line in text.splitlines():
            line = line.strip()
            if line:
                root.after(0, append_robot_line, line)


def append_robot_line(line):
    output_box.insert("end", "ROBOT: " + line + "\n")
    output_box.see("end")


def test_robot():
    try:
        settings = get_settings()
    except Exception as exc:
        messagebox.showerror("Settings error", str(exc))
        return

    robot_test_button.configure(state="disabled")
    udp_status.set(
        "Sending 'X' to "
        + settings["robot_host"] + ":" + str(settings["robot_port"])
        + " ..."
    )

    threading.Thread(
        target=robot_test_worker,
        args=(settings,),
        daemon=True
    ).start()


def robot_test_worker(settings):
    destination = (
        settings["robot_host"] + ":" + str(settings["robot_port"])
    )

    try:
        ack_event.clear()
        udp_send("X", settings)
    except Exception as exc:
        root.after(0, udp_status.set,
                   "UDP send failed: " + str(exc))
        root.after(0, lambda: robot_test_button.configure(state="normal"))
        return

    # The ESP32 replies to the sender address, so our listener thread
    # will receive the ACK and set ack_event.
    got_ack = ack_event.wait(timeout=3.0)

    if got_ack:
        root.after(0, udp_status.set,
                   "Robot OK — ACK received from " + destination
                   + ". See ROBOT: lines in the log.")
    else:
        root.after(0, udp_status.set,
                   "No ACK from " + destination + " within 3 s. "
                   "Check: robot IP/port, robot powered + WiFi connected, "
                   "same network, AP isolation off.")

    root.after(0, lambda: robot_test_button.configure(state="normal"))


def on_live_toggle():
    state = "LIVE: commands are sent to the robot." if live_var.get() \
        else "DRY RUN: commands are only displayed."

    command_status.set(state)
    save_settings_file(silent=True)

# =========================================================
# MODEL REQUEST
# =========================================================

def call_model(messages, settings):
    headers = {"Content-Type": "application/json"}

    if settings["token"]:
        headers["Authorization"] = "Bearer " + settings["token"]

    if settings["provider"] == "Ollama":
        payload = {
            "model": settings["model"],
            "messages": messages,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": sorted(INTENTS),
                    },
                    "size": {
                        "type": "string",
                        "enum": sorted(DURATIONS),
                    },
                },
                "required": ["intent", "size"],
            },
            "options": {"temperature": 0},
        }

        if settings["think_off"]:
            payload["think"] = False

        response = requests.post(
            settings["url"],
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")

    else:
        payload = {
            "model": settings["model"],
            "messages": messages,
            "stream": False,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        if settings["think_off"]:
            payload["think"] = False

        response = requests.post(
            settings["url"],
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])

        if not choices:
            raise ValueError("API returned no choices.")

        content = choices[0].get("message", {}).get("content", "")

        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict)
            )

    content = str(content).strip()

    if not content:
        raise ValueError("Model returned empty content.")

    if "<think>" in content.lower() or "</think>" in content.lower():
        raise ValueError("Model returned reasoning instead of JSON.")

    return content

# =========================================================
# SERVO COMMAND TRANSLATION
# =========================================================

def clean_json(raw):
    """Remove markdown code fences if the model added them."""
    text = raw.strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    return text


def parse_intent(raw):
    data = json.loads(clean_json(raw))

    intent = data.get("intent")
    size = data.get("size")

    if intent not in INTENTS:
        raise ValueError("Invalid intent: " + str(intent))

    if size not in DURATIONS:
        raise ValueError("Invalid size: " + str(size))

    return intent, size


def make_command(intent, size):
    global last_direction

    duration = DURATIONS[size]

    if intent == "move_left":
        last_direction = "L"
        return f"L{duration}"

    if intent == "move_right":
        last_direction = "R"
        return f"R{duration}"

    if intent == "more":
        if last_direction is None:
            return "X"
        return f"{last_direction}{duration}"

    if intent == "reverse":
        if last_direction is None:
            return "X"
        last_direction = "R" if last_direction == "L" else "L"
        return f"{last_direction}{duration}"

    if intent == "stop" or intent == "unclear":
        last_direction = None
        return "X"

    if intent == "center":
        # Firmware command: return to estimated home position
        last_direction = None
        return "HOME"

    if intent == "happy":
        return "H3"

    if intent == "sad":
        return "S3"

    last_direction = None
    return "X"

# =========================================================
# COMMAND TESTER TAB
# =========================================================

def send_command():
    global busy

    if busy:
        return

    text = input_box.get("1.0", "end").strip()
    if not text:
        return

    try:
        settings = get_settings()
    except Exception as exc:
        messagebox.showerror("Settings error", str(exc))
        notebook.select(settings_tab)
        return

    input_box.delete("1.0", "end")
    busy = True
    send_button.configure(state="disabled")
    command_status.set("Waiting for model...")

    output_box.insert("end", "\nYOU: " + text + "\n")
    output_box.see("end")

    threading.Thread(
        target=command_worker,
        args=(text, settings),
        daemon=True,
    ).start()


def command_worker(text, settings):
    global history

    try:
        new_history = history + [
            {"role": "user", "content": text}
        ]

        raw = call_model(new_history, settings)
        intent, size = parse_intent(raw)

        history = new_history + [
            {"role": "assistant", "content": raw}
        ]

        command = make_command(intent, size)

        sent = False
        send_error = None

        if settings["live_send"]:
            try:
                udp_send(command, settings)
                sent = True
            except Exception as exc:
                send_error = str(exc)

        root.after(
            0, display_result,
            raw, intent, size, command, None, sent, send_error, settings
        )

    except Exception as exc:
        root.after(
            0, display_result,
            "", "", "", "", str(exc), False, None, None
        )


def display_result(raw, intent, size, command, error,
                   sent=False, send_error=None, settings=None):
    global busy

    if error:
        output_box.insert("end", "ERROR: " + error + "\n")
        command_status.set("Request failed.")
    else:
        output_box.insert("end", "LLM JSON: " + raw + "\n")
        output_box.insert("end", "INTENT: " + intent + "\n")
        output_box.insert("end", "SIZE: " + size + "\n")
        output_box.insert("end", "ESP32 COMMAND: " + command + "\n")

        if settings and settings["live_send"]:
            if sent:
                output_box.insert(
                    "end",
                    "SENT over UDP -> "
                    + settings["robot_host"] + ":"
                    + str(settings["robot_port"]) + "\n"
                )
                command_status.set(
                    "Sent. Waiting for ROBOT: ACK lines..."
                )
            else:
                output_box.insert(
                    "end",
                    "SEND FAILED: " + str(send_error) + "\n"
                )
                command_status.set("UDP send failed.")
        else:
            output_box.insert(
                "end",
                "(dry run — tick 'Send commands to robot' to move the servo)\n"
            )
            command_status.set("Generated only — dry run.")

    output_box.see("end")
    send_button.configure(state="normal")
    busy = False


def reset_conversation():
    global history, last_direction

    if busy:
        return

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    last_direction = None
    output_box.delete("1.0", "end")
    command_status.set("Conversation reset.")

# =========================================================
# MAIN WINDOW AND TABS
# =========================================================

root = tk.Tk()
root.title("LLM Servo Controller (ESP32-S3 over UDP)")
root.geometry("880x760")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# ---------------- Settings tab ----------------

settings_tab = ttk.Frame(notebook, padding=12)
notebook.add(settings_tab, text="Settings")

provider_var = tk.StringVar(value="Ollama")
url_var = tk.StringVar(value=OLLAMA_URL)
token_var = tk.StringVar(value="")
model_var = tk.StringVar(value=DEFAULT_MODEL)
think_var = tk.BooleanVar(value=True)
robot_host_var = tk.StringVar(value=DEFAULT_ROBOT_HOST)
robot_port_var = tk.StringVar(value=str(DEFAULT_ROBOT_PORT))
live_var = tk.BooleanVar(value=False)

settings_status = tk.StringVar(value="Configure your LLM connection.")
udp_status = tk.StringVar(value="Robot not tested yet.")

settings_tab.columnconfigure(1, weight=1)

ttk.Label(settings_tab, text="Provider").grid(
    row=0, column=0, sticky="w", padx=5, pady=8
)

provider_box = ttk.Combobox(
    settings_tab,
    textvariable=provider_var,
    values=["Ollama", "OpenAI-compatible API"],
    state="readonly",
    width=30,
)
provider_box.grid(row=0, column=1, sticky="ew", padx=5, pady=8)
provider_box.bind("<<ComboboxSelected>>", update_provider_ui)

ttk.Label(settings_tab, text="API URL").grid(
    row=1, column=0, sticky="w", padx=5, pady=8
)

url_entry = ttk.Entry(settings_tab, textvariable=url_var)
url_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=8)

ttk.Label(settings_tab, text="API token").grid(
    row=2, column=0, sticky="w", padx=5, pady=8
)

token_entry = ttk.Entry(
    settings_tab, textvariable=token_var, show="*"
)
token_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=8)

ttk.Label(settings_tab, text="Model name").grid(
    row=3, column=0, sticky="w", padx=5, pady=8
)

model_entry = ttk.Entry(settings_tab, textvariable=model_var)
model_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=8)

think_check = ttk.Checkbutton(
    settings_tab,
    text="Disable thinking where supported",
    variable=think_var,
)
think_check.grid(row=4, column=1, sticky="w", padx=5, pady=8)

ttk.Separator(settings_tab, orient="horizontal").grid(
    row=5, column=0, columnspan=2, sticky="ew", pady=10
)

ttk.Label(
    settings_tab,
    text="Robot (ESP32-S3) over UDP",
    font=("Arial", 11, "bold"),
).grid(row=6, column=0, columnspan=2, sticky="w", padx=5)

ttk.Label(settings_tab, text="Robot host / IP").grid(
    row=7, column=0, sticky="w", padx=5, pady=8
)

host_entry = ttk.Entry(settings_tab, textvariable=robot_host_var)
host_entry.grid(row=7, column=1, sticky="ew", padx=5, pady=8)

ttk.Label(settings_tab, text="Robot UDP port").grid(
    row=8, column=0, sticky="w", padx=5, pady=8
)

port_entry = ttk.Entry(settings_tab, textvariable=robot_port_var, width=8)
port_entry.grid(row=8, column=1, sticky="w", padx=5, pady=8)

robot_test_button = ttk.Button(
    settings_tab,
    text="Test robot (UDP)",
    command=test_robot,
)
robot_test_button.grid(row=9, column=0, padx=5, pady=8, sticky="w")

ttk.Label(
    settings_tab,
    textvariable=udp_status,
    wraplength=520,
    justify="left",
).grid(row=9, column=1, sticky="w", padx=5, pady=8)

ttk.Separator(settings_tab, orient="horizontal").grid(
    row=10, column=0, columnspan=2, sticky="ew", pady=10
)

test_button = ttk.Button(
    settings_tab,
    text="Test LLM connection",
    command=test_connection,
)
test_button.grid(row=11, column=0, padx=5, pady=12, sticky="w")

ttk.Button(
    settings_tab,
    text="Save settings & open tester",
    command=save_settings,
).grid(row=11, column=1, padx=5, pady=12, sticky="e")

ttk.Label(
    settings_tab,
    textvariable=settings_status,
    wraplength=650,
).grid(row=12, column=0, columnspan=2, sticky="w", padx=5, pady=10)

ttk.Label(
    settings_tab,
    text=(
        "Ollama URL example: http://localhost:11434\n"
        "Robot host: the ESP32 IP printed at boot (or robot1.local).\n"
        "Robot UDP port must match UDP_PORT in the ESP32 sketch (3361).\n"
        "'Test robot (UDP)' sends X (stop) and waits for the robot's ACK."
    ),
    justify="left",
).grid(row=13, column=0, columnspan=2, sticky="w", padx=5, pady=10)

# ---------------- Command Tester tab ----------------

command_tab = ttk.Frame(notebook, padding=10)
notebook.add(command_tab, text="Command Tester")

ttk.Label(
    command_tab,
    text="Natural-language servo command tester",
    font=("Arial", 12, "bold"),
).pack(pady=6)

live_check = ttk.Checkbutton(
    command_tab,
    text="Send commands to robot (live mode) — unticked = dry run",
    variable=live_var,
    command=on_live_toggle,
)
live_check.pack(pady=4)

output_box = scrolledtext.ScrolledText(
    command_tab, height=22, wrap=tk.WORD
)
output_box.pack(fill="both", expand=True, pady=6)

input_box = tk.Text(command_tab, height=3, wrap=tk.WORD)
input_box.pack(fill="x", pady=6)
input_box.bind(
    "<Control-Return>",
    lambda event: send_command(),
)

button_row = ttk.Frame(command_tab)
button_row.pack(pady=5)

send_button = ttk.Button(
    button_row,
    text="Generate command",
    command=send_command,
)
send_button.pack(side="left", padx=5)

ttk.Button(
    button_row,
    text="Reset conversation",
    command=reset_conversation,
).pack(side="left", padx=5)

command_status = tk.StringVar(
    value="DRY RUN: commands are only displayed. "
          "Tick 'Send commands to robot' to move the servo."
)

ttk.Label(
    command_tab,
    textvariable=command_status,
    wraplength=700,
).pack(pady=6)

# ---------------- Startup ----------------

def on_close():
    save_settings_file(silent=True)
    root.destroy()


if load_settings_file():
    settings_status.set(
        "Settings loaded from " + SETTINGS_FILE
    )
else:
    settings_status.set(
        "No saved settings found — defaults loaded. "
        "Fill in and press 'Save settings'."
    )

update_provider_ui()
on_live_toggle()   # sync status line with loaded live-mode state

# Start robot ACK listener
threading.Thread(target=udp_listener, daemon=True).start()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()