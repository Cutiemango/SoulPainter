import socket
import selectors
import threading
import time
import random
from queue import Queue

HOST = '0.0.0.0'
PORT = 48763

questions = ["蘋果", "柳橙", "芒果", "西瓜", "奇異果", "芭樂", "香蕉", "番茄", "檸檬", "哈密瓜", "水蜜桃", "李子", "楊桃"]
running = True
selector = selectors.DefaultSelector()


class Player:
    def __init__(self, conn, name="Unnamed Player"):
        self.conn = conn
        self.addr = conn.getpeername()
        self.name = name
        self.update_lock = threading.Lock()
        self.step = 0

    def __eq__(self, other):
        if isinstance(other, Player):
            return self.conn.getpeername() == other.conn.getpeername()
        return False

    def is_disconnected(self):
        return self.conn.fileno() == -1

    def paint(self, payload):
        send_packet(self.conn, "G", f"PAINT,{payload}")

    def update_palette(self, history):
        while not self.update_lock.acquire():
            pass
        while self.step < len(history):
            time.sleep(0.01)
            self.paint(history[self.step])
            self.step += 1
        self.update_lock.release()

    def clear_palette(self):
        while not self.update_lock.acquire():
            pass
        self.step = 0
        self.update_lock.release()
        send_packet(self.conn, "G", "CLEAR")

    def get_turn(self):
        send_packet(self.conn, "G", "TURN")

    def set_timer(self, text, seconds):
        send_packet(self.conn, "G", f"TIME,{text},{seconds}")

    def lock_palette(self):
        send_packet(self.conn, "G", "LOCK")

    def send_grid_status(self, status):
        send_packet(self.conn, "G", f"GRID_STATUS,{status}")

    def send_grid_query(self):
        send_packet(self.conn, "G", "GRID_QUERY")

    def change_name(self, new_name):
        self.name = new_name

    def send_game_message(self, pkt_type, msg):
        send_packet(self.conn, "N", pkt_type + "," + msg)

    def send_player_message(self, msg):
        send_packet(self.conn, "C", msg)


class GameServer:
    def __init__(self):
        self.connected_players = {}
        self.paint_queue = Queue()
        self.counter = GameCounter(self)
        self.counter.start()
        self.painting_player = None
        self.painting_answer = ""
        self.guessed = set()
        self.scoreboard = {}
        self.operation_history = []
        self.game_running = False

    def player_join(self, conn, name):
        addr = conn.getpeername()

        duplicate_name = False
        for player in self.connected_players.values():
            if name == player.name:
                duplicate_name = True
                break
        if duplicate_name:
            send_packet(conn, "N", "DUPNAME,")
            return
        else:
            send_packet(conn, "N", "WELCOME,")

        new_player = Player(conn, name)
        self.connected_players[addr] = new_player
        self.scoreboard[addr] = 0
        self.add_to_paint_queue(new_player)

        print(f"[GameServer] {new_player.name} ({addr}) has joined the game")

        for player in self.connected_players.values():
            player.send_game_message("INFO", f"[系統] {new_player.name} 加入了遊戲")
            player.send_game_message("SCORE", f"{new_player.name},{self.scoreboard[addr]}")
            new_player.send_game_message("SCORE", f"{player.name},{self.scoreboard[addr]}")

        new_player.lock_palette()

        if not self.game_running:
            self.check_next_turn()
        else:
            new_player.set_timer(f"Turn of {self.painting_player.name}", self.counter.counter)

        upd = threading.Thread(target=new_player.update_palette, args=[self.operation_history])
        upd.start()

    def player_disconnect(self, addr):
        player_name = self.connected_players[addr].name
        print(f"[GameServer] {player_name} ({addr}) has left the game")

        self.connected_players.pop(addr)
        self.scoreboard.pop(addr)

        is_painter = self.painting_player is not None and addr == self.painting_player.addr

        for player in self.connected_players.values():
            player.send_game_message("INFO", f"[系統] {player_name} 離開了遊戲")
            if is_painter:
                player.send_game_message("SCORE", f"{player_name},-1")

        if is_painter:
            self.skip_painter()

    def query_palette(self):
        if self.painting_player is not None:
            self.painting_player.send_grid_query()

    def add_to_paint_queue(self, player):
        self.paint_queue.put(player)

    def turn_expired(self):
        self.painting_player.lock_palette()
        self.paint_queue.put(self.painting_player)
        self.painting_player = None
        for player in self.connected_players.values():
            if self.painting_answer != "":
                player.send_game_message("INFO", f"正確答案是：「{self.painting_answer}」")
            player.clear_palette()
            player.set_timer("Take a break", 5)
        self.counter.count("break")

    def decode_packet(self, sender_conn, channel, pkt_type, payload):
        addr = sender_conn.getpeername()
        if channel == "G":
            if pkt_type == "JOIN":
                self.player_join(sender_conn, payload)
            elif pkt_type == "PAINT":
                sender = self.connected_players[addr]
                self.operation_history.append(payload)
                for player in self.connected_players.values():
                    if player == sender: continue
                    if player.update_lock.locked(): continue
                    if player.step == len(self.operation_history) - 1:
                        player.paint(self.operation_history[-1])
                        player.step += 1
                    else:
                        print(f"[GameServer] Started update thread for {player.name} ({player.addr})")
                        upd = threading.Thread(target=player.update_palette, args=[self.operation_history])
                        upd.start()
        elif channel == "N":
            sender = self.connected_players[addr]
            if pkt_type == "GUESS":
                if self.painting_player is None or sender == self.painting_player or addr in self.guessed: return
                if payload == self.painting_answer:
                    self.guessed.add(addr)
                    self.scoreboard[addr] += 1
                    for player in self.connected_players.values():
                        player.send_game_message("INFO", f"[系統] {sender.name} 猜到了答案！")
                        player.send_game_message("SCORE", f"{sender.name},{self.scoreboard[addr]}")

                    if len(self.guessed) == len(self.connected_players) - 1:
                        for player in self.connected_players.values():
                            player.send_game_message("INFO", f"[系統] 大家都猜到了答案！真是傑作！")
                        self.painting_player.lock_palette()
                        self.paint_queue.put(self.painting_player)
                        self.skip_painter()
                else:
                    for player in self.connected_players.values():
                        player.send_game_message("INFO", f"{sender.name}: {payload}")

        elif channel == "C":
            sender = self.connected_players[addr]
            for player in self.connected_players.values():
                player.send_player_message(f"{sender.name}: {payload}")

    def skip_painter(self):
        self.painting_player = None
        for player in self.connected_players.values():
            player.clear_palette()
            player.set_timer("Take a break", 5)
        self.counter.count("break")

    def check_next_turn(self):
        if self.painting_player is not None: return
        if len(self.connected_players) > 1:
            while not self.paint_queue.empty():
                cur_player = self.paint_queue.get()
                if cur_player.is_disconnected(): continue
                self.next_turn(cur_player)
                break
        else:
            for player in self.connected_players.values():
                player.send_game_message("INFO", "[系統] 人數不足，等待其他玩家進入")
                player.set_timer("Waiting for players", 0)
            self.game_running = False

    def next_turn(self, cur_player):
        self.operation_history = []
        self.guessed = set()
        for player in self.connected_players.values():
            if not self.game_running:
                player.send_game_message("INFO", f"[系統] 遊戲開始！")
            player.send_game_message("INFO", f"[系統] {cur_player.name} 的回合")
            player.clear_palette()
            player.set_timer(f"Turn of {cur_player.name}", 60)
        self.game_running = True
        self.painting_answer = random.sample(questions, 1)[0]
        self.painting_player = cur_player
        cur_player.get_turn()
        cur_player.send_game_message("INFO", f"[系統] 請畫出「{self.painting_answer}」")
        self.counter.count("turn")


class GameCounter(threading.Thread):
    def __init__(self, server):
        super().__init__()
        self.server = server
        self.lock = threading.Lock()
        self.counter = -1
        self.task = "turn"
        self.stop = False

    def run(self):
        while not self.stop:
            time.sleep(1)
            while not self.lock.acquire():
                pass
            if self.counter >= 0:
                self.counter -= 1
            self.lock.release()
            if self.counter == 0:
                if self.task == "turn":
                    self.server.turn_expired()
                elif self.task == "break":
                    self.server.check_next_turn()

    def count(self, task):
        self.task = task
        while not self.lock.acquire():
            pass
        if self.task == "turn":
            self.counter = 60
        elif self.task == "break":
            self.counter = 5
        self.lock.release()

    def stop(self):
        self.stop = True


def send_packet(conn, channel, msg):
    conn.sendall(f"{channel},{msg}@".encode())


def read_data_from_client(conn, addr, game_server):
    try:
        msg = str(conn.recv(4096), encoding='utf-8')
        if msg:
            print(f"[From client {addr}]: {msg}")
            packets = msg.split("@")
            for packet in packets:
                if len(packet) == 0: continue
                channel, channel_pkt = packet.split(",", 1)
                if channel == "G" or channel == "N":
                    pkt_type, payload = channel_pkt.split(",", 1)
                    game_server.decode_packet(conn, channel, pkt_type, payload)
                else:
                    game_server.decode_packet(conn, channel, None, channel_pkt)
        else:
            game_server.player_disconnect(addr)
            selector.unregister(conn)
            conn.close()
    except ConnectionError:
        print(f"[Server] Lost connection to {addr}")
        pass


def accept(server, game_server):
    conn, addr = server.accept()
    conn.setblocking(False)

    print(f"[Server] Server is connected to {addr}")

    selector.register(conn, selectors.EVENT_READ, (read_data_from_client, addr))


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(False)
    server.bind((HOST, PORT))
    server.listen(10)

    print(f"[Server] Server is listening on {(HOST, PORT)}")

    game_server = GameServer()

    selector.register(server, selectors.EVENT_READ, (accept,))

    while running:
        for key, mask in selector.select():
            data = key.data
            callback = data[0]
            client_socket = key.fileobj
            if len(data) > 1:
                callback(client_socket, data[1], game_server)
            else:
                callback(client_socket, game_server)

    print(f"[Server] Server is shutting down...")

    if len(game_server.connected_players) > 0:
        server.shutdown(socket.SHUT_RD)
    server.close()
    selector.close()


if __name__ == "__main__":
    main()
