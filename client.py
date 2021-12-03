import socket
import threading
import game
from queue import Queue

HOST = '127.0.0.1'
PORT = 8000
SCREEN_WIDTH, SCREEN_HEIGHT = 960, 770

game_msg_queue = Queue()
chat_msg_queue = Queue()


def threaded_client(conn):
    while True:
        try:
            msg = str(conn.recv(1024), encoding='utf-8')
            if msg:
                print(f"[From server {(HOST, PORT)}]: {msg}")
                if msg.startswith("G"):
                    for packet in msg.split("@"):
                        if len(packet) == 0: continue
                        game_msg_queue.put(packet[2:])
            else:
                break
        except Exception as e:
            print(f'[Client] Error handling message from server: {e}')
            break
    conn.close()
    print(f"[Client] Disconnected from server")


def game_thread(conn):
    game.main(game_msg_queue, conn)


def connect(host, port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"[Client] Connecting to {(host, port)}...")
    try:
        client.connect((host, port))
        print(f"[Client] Connected to {(HOST, PORT)}")
        return client
    except Exception as e:
        print(f'[Client] Error connecting the server: {e}')
        return None


def main():
    conn = connect(HOST, PORT)
    if not conn: return

    chat = threading.Thread(target=threaded_client, args=[conn])
    chat.start()

    game_thr = threading.Thread(target=game_thread, args=[conn])
    game_thr.start()
    game_thr.join()
    chat.join()
    # try:
    #     while True:
    #         content = input()
    #         if content == 'quit':
    #             break
    #         conn.sendall(content.encode())
    # except ConnectionError:
    #     pass
    # conn.close()
    # print(f"[Client] Quitted")


if __name__ == "__main__":
    main()
