import socket
import selectors

HOST = '127.0.0.1'
PORT = 8000
running = True
connected_clients = []
selector = selectors.DefaultSelector()


def read_data_from_client(conn):
    addr = conn.getpeername()
    try:
        msg = str(conn.recv(1024), encoding='utf-8')
        if msg != "bye" and msg != "":
            print(f"[From client {addr}]: {msg}")
            for client in connected_clients:
                if conn == client: continue
                client.sendall(f"[From {addr}]: {msg}".encode())
            return
    except ConnectionError:
        pass
    connected_clients.remove(conn)
    selector.unregister(conn)
    conn.close()
    print(f"[Server] Lost connection to {addr}")


def accept(server):
    conn, addr = server.accept()
    conn.setblocking(False)

    print(f"[Server] Server is connected to {addr}")
    connected_clients.append(conn)

    selector.register(conn, selectors.EVENT_READ, read_data_from_client)


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(False)
    server.bind((HOST, PORT))
    server.listen(10)

    print(f"[Server] Server is listening on {(HOST, PORT)}")

    selector.register(server, selectors.EVENT_READ, accept)

    while running:
        for key, mask in selector.select():
            callback = key.data
            callback(key.fileobj)

    print(f"[Server] Server is shutting down...")

    if len(connected_clients) > 0:
        server.shutdown(socket.SHUT_RD)
    server.close()
    selector.close()


if __name__ == "__main__":
    main()
