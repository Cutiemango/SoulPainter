import socket
import threading
import game
import re
import tkinter as tk
from queue import Queue

APP_WIDTH, APP_HEIGHT = 400, 770
CHAT_FONT = ("微軟正黑體", 12)
GLOBAL_FONT = ("Consolas", 16)
IP_REGEX = r"\d{1,3}(\.\d{1,3}){3}"
PORT_REGEX = r"\d{4,5}"
NAME_REGEX = r"[a-zA-Z0-9_]+"

app = tk.Tk()
client: socket.socket = None
connect_parameters = {
    "host": "127.0.0.1",
    "port": "48763",
    "name": "Kirito"
}
game_msg_queue = Queue()

tk_elements = {}
has_focus = {}
score_dict = {}


def threaded_socket():
    print("[Client] Socket thread created")
    global client
    while True:
        try:
            msg = str(client.recv(4096), encoding='utf-8')
            if msg:
                print(f"[From server]: {msg}")
                packets = msg.split("@")
                for packet in packets:
                    data = packet.split(",", 1)
                    if data[0] == "G":
                        game_msg_queue.put(data[1])
                    elif data[0] == "N":
                        pkt_type, payload = data[1].split(",", 1)
                        decode_packet(pkt_type, payload)
                    elif data[0] == "C":
                        if "chat_message" in tk_elements:
                            insert_message(tk_elements["chat_message"], data[1] + "\n")
            else:
                break
        except Exception as e:
            print(f'[Client] Error handling message from server: {e}')
            break
    client.close()
    print(f"[Client] Disconnected from server")


def decode_packet(pkt_type, payload):
    if pkt_type == "INFO":
        if "game_message" in tk_elements:
            insert_message(tk_elements["game_message"], payload + "\n")
    elif pkt_type == "SCORE":
        name, score = payload.split(",")
        if score == "-1":
            score_dict.pop(name)
        else:
            score_dict[name] = score
        update_scoreboard()
    elif pkt_type == "WELCOME":
        enter_game_chat()
    elif pkt_type == "DUPNAME":
        insert_message(tk_elements["response_message"], "", True)
        insert_message(tk_elements["response_message"], "Name has already been used. Please choose a new name.")


def update_scoreboard():
    if "scoreboard" not in tk_elements: return
    box = tk_elements["scoreboard"]
    insert_message(box, "", True)
    box.config(state=tk.NORMAL)
    box.insert(tk.END, f"Name" + " " * max(15 - len("Name"), 1) + "Score\n")
    for name, score in sorted(score_dict.items(), key=lambda x: (-int(x[1]), x[0])):
        line = name
        line += " " * max(15 - len(name), 1)
        line += " " * max(5 - len(str(score)), 1)
        line += score
        box.insert(tk.END, line + "\n")
    box.config(state=tk.DISABLED)


def insert_message(entry, message, clear=False):
    entry.config(state=tk.NORMAL)
    if clear: entry.delete('1.0' if isinstance(entry, tk.Text) else 0, tk.END)
    entry.insert(tk.END, message)
    if isinstance(entry, tk.Text): entry.see(tk.END)
    entry.config(state=tk.DISABLED)


def send_game_message(entry):
    client.sendall(f"N,GUESS,{entry.get()}".encode())
    insert_message(entry, "", True)
    entry.config(state=tk.NORMAL)


def send_chat_message(entry):
    client.sendall(f"C,{entry.get()}".encode())
    insert_message(entry, "", True)
    entry.config(state=tk.NORMAL)


def app_close():
    if client is not None: client.close()
    app.destroy()


def set_connect_params(key, val):
    if has_focus[key]:
        connect_parameters[key] = val
        print(f"[Client] Connect param {key} has been set to {val}")


def check_connect_params():
    errors = []
    if not re.fullmatch(IP_REGEX, connect_parameters["host"]):
        errors.append("Invalid ip address. Please check your input.")
    if not re.fullmatch(PORT_REGEX, connect_parameters["port"]):
        errors.append("Invalid port. Please check your input.")
    if not re.fullmatch(NAME_REGEX, connect_parameters["name"]):
        errors.append("Name can only contain english letters, numbers and underscores.")
    return errors


def threaded_game_client():
    global client
    print("[Client] Starting game client")
    game.main(game_msg_queue, client)
    print("[Client] Game client terminated")


def connect():
    errors = check_connect_params()
    if len(errors) > 0:
        insert_message(tk_elements["response_message"], "", True)
        for error in errors:
            insert_message(tk_elements["response_message"], error + "\n")
        return
    host = connect_parameters["host"]
    port = int(connect_parameters["port"])
    global client
    print(f"[Client] Connecting to {(host, port)}...")
    try:
        if client is None or client.fileno() == -1:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client.connect((host, port))
            print(f"[Client] Connected to {(host, port)}")
            socket_thread = threading.Thread(target=threaded_socket)
            socket_thread.start()
        client.sendall(f"G,JOIN,{connect_parameters['name']}".encode())
    except Exception as e:
        print(f'[Client] Error connecting the server: {e}')
        insert_message(tk_elements["response_message"], "", True)
        insert_message(tk_elements["response_message"], f"Error connecting the server: {e}\n")
        client = None


def enter_game_chat():
    game_thread = threading.Thread(target=threaded_game_client)
    game_thread.start()

    tk_elements["lobby_frame"].pack_forget()
    tk_elements["message_frame"].pack(side=tk.TOP)
    tk_elements["message_frame"].pack_propagate(0)


def enter_lobby():
    tk_elements["message_frame"].pack_forget()
    tk_elements["lobby_frame"].pack(side=tk.TOP)
    tk_elements["lobby_frame"].pack_propagate(0)


def set_focus(widget, focus):
    has_focus[widget] = focus


def main():
    app.title("SoulPainter Chat Client")
    app.geometry("%dx%d" % (APP_WIDTH, APP_HEIGHT))

    main_frame = tk.Frame(app,
                          bg="white",
                          highlightbackground="black", highlightthickness=1,
                          width=APP_WIDTH,
                          height=APP_HEIGHT)
    main_frame.pack(side=tk.TOP)
    main_frame.pack_propagate(0)

    lobby_frame = tk.Frame(main_frame,
                           highlightbackground="black", highlightthickness=1,
                           width=APP_WIDTH,
                           height=APP_HEIGHT)
    tk_elements["lobby_frame"] = lobby_frame

    header_label = tk.Label(lobby_frame, font=("Consolas", 18), text="Connect To Game Server")
    header_label.pack(side=tk.TOP, pady=(50, 0))

    ip_label = tk.Label(lobby_frame, font=("Consolas", 16), text="Server IP")
    ip_label.pack(side=tk.TOP, pady=(50, 0))

    ip_entry = tk.Entry(lobby_frame,
                        width=15,
                        highlightbackground="black", highlightthickness=1,
                        font=GLOBAL_FONT)
    ip_entry.pack(side=tk.TOP, pady=(10, 0))
    ip_entry.insert(tk.END, f"{connect_parameters['host']}")
    ip_entry.bind('<FocusIn>', lambda event: set_focus('host', True))
    ip_entry.bind('<FocusOut>', lambda event: set_focus('host', False))
    ip_entry.bind("<KeyRelease>", lambda event: set_connect_params('host', event.widget.get()))

    port_label = tk.Label(lobby_frame, font=("Consolas", 16), text="Port")
    port_label.pack(side=tk.TOP, pady=(50, 0))

    port_entry = tk.Entry(lobby_frame,
                          width=10,
                          highlightbackground="black", highlightthickness=1,
                          font=GLOBAL_FONT)
    port_entry.pack(side=tk.TOP, pady=(10, 0))
    port_entry.insert(tk.END, f"{connect_parameters['port']}")
    port_entry.bind('<FocusIn>', lambda event: set_focus('port', True))
    port_entry.bind('<FocusOut>', lambda event: set_focus('port', False))
    port_entry.bind("<KeyRelease>", lambda event: set_connect_params('port', event.widget.get()))

    name_label = tk.Label(lobby_frame, font=("Consolas", 16), text="Nickname")
    name_label.pack(side=tk.TOP, pady=(50, 0))

    name_entry = tk.Entry(lobby_frame,
                          width=10,
                          highlightbackground="black", highlightthickness=1,
                          font=GLOBAL_FONT)
    name_entry.pack(side=tk.TOP, pady=(10, 0))
    name_entry.insert(tk.END, f"{connect_parameters['name']}")
    name_entry.bind('<FocusIn>', lambda event: set_focus('name', True))
    name_entry.bind('<FocusOut>', lambda event: set_focus('name', False))
    name_entry.bind("<KeyRelease>", lambda event: set_connect_params('name', event.widget.get()))

    connect_btn = tk.Button(lobby_frame,
                            font=GLOBAL_FONT,
                            text="Link Start",
                            command=connect)
    connect_btn.pack(side=tk.TOP, pady=(30, 0))

    response_message = tk.Text(lobby_frame,
                               width=APP_WIDTH,
                               height=5,
                               bg="white",
                               highlightbackground="#505050", highlightthickness=1,
                               font=CHAT_FONT)
    response_message.pack(side=tk.TOP, padx=30, pady=(20, 0))
    response_message.config(state=tk.DISABLED)
    tk_elements["response_message"] = response_message

    message_frame = tk.Frame(main_frame,
                             bg="white",
                             highlightbackground="black", highlightthickness=1,
                             width=APP_WIDTH,
                             height=APP_HEIGHT)
    tk_elements["message_frame"] = message_frame

    game_message_label = tk.Label(message_frame, bg="white", font=GLOBAL_FONT, text="Game Info / Guess")
    game_message_label.pack(side=tk.TOP, pady=10)
    game_message = tk.Text(message_frame,
                           width=APP_WIDTH,
                           height=8,
                           bg="white",
                           highlightbackground="#505050", highlightthickness=2,
                           font=CHAT_FONT)
    game_message.pack(side=tk.TOP, padx=10)
    game_message.config(state=tk.DISABLED)
    tk_elements["game_message"] = game_message

    game_message_entry = tk.Entry(message_frame,
                                  width=APP_WIDTH,
                                  highlightbackground="#505050", highlightthickness=2,
                                  font=CHAT_FONT)
    game_message_entry.pack(side=tk.TOP, padx=10)
    game_message_entry.bind('<Return>', lambda event: send_game_message(event.widget))

    chat_message_label = tk.Label(message_frame, bg="white", font=GLOBAL_FONT, text="Chat Room")
    chat_message_label.pack(side=tk.TOP, pady=10)
    chat_message = tk.Text(message_frame,
                           width=APP_WIDTH,
                           height=8,
                           bg="white",
                           highlightbackground="#505050", highlightthickness=2,
                           font=CHAT_FONT)
    chat_message.pack(side=tk.TOP, padx=10)
    chat_message.config(state=tk.DISABLED)
    tk_elements["chat_message"] = chat_message

    chat_message_entry = tk.Entry(message_frame,
                                  width=APP_WIDTH,
                                  highlightbackground="#505050", highlightthickness=2,
                                  font=CHAT_FONT)
    chat_message_entry.pack(side=tk.TOP, padx=10)
    chat_message_entry.bind('<Return>', lambda event: send_chat_message(event.widget))

    scoreboard_label = tk.Label(message_frame, bg="white", font=GLOBAL_FONT, text="Scoreboard")
    scoreboard_label.pack(side=tk.TOP, pady=10)
    scoreboard = tk.Text(message_frame,
                         width=int(0.6 * APP_WIDTH),
                         bg="white",
                         highlightbackground="#505050", highlightthickness=2,
                         font=GLOBAL_FONT)
    scoreboard.pack(side=tk.TOP, padx=60, pady=(0, 20), ipadx=30)
    scoreboard.config(state=tk.DISABLED)
    tk_elements["scoreboard"] = scoreboard

    enter_lobby()

    app.protocol("WM_DELETE_WINDOW", app_close)
    app.resizable(False, False)
    app.mainloop()


if __name__ == "__main__":
    main()
