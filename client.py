import socket
import threading
import pygame

HOST = '127.0.0.1'
PORT = 8000
SCREEN_WIDTH, SCREEN_HEIGHT = 960, 770


def threaded_client(conn):
    while True:
        try:
            msg = str(conn.recv(1024), encoding='utf-8')
            if msg:
                print(msg)
            else:
                break
        except Exception as e:
            print(f'[Client] Error handling message from server: {e}')
            break
    conn.close()
    print(f"[Client] Disconnected from server")


def draw_circle(screen, x, y):
    pygame.draw.circle(screen, (0, 0, 255), (x, y), 5)


def game_thread(conn):
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    isPressed = False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                isPressed = True
            elif event.type == pygame.MOUSEBUTTONUP:
                isPressed = False
            elif event.type == pygame.MOUSEMOTION and isPressed is True:
                isPressed = True
                (x, y) = pygame.mouse.get_pos()  # returns the position of mouse cursor
                draw_circle(screen, x, y)
                conn.sendall(f"Clicked: {(x, y)}".encode())
            elif event.type == pygame.QUIT:
                pygame.quit()
                conn.close()
                return
        pygame.display.flip()


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

    game = threading.Thread(target=game_thread, args=[conn])
    game.start()
    game.join()
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
