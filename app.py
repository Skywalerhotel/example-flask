import socket
import threading
import select
import os

BUFFER_SIZE = 8192
LISTEN_PORT = int(os.environ.get("PORT", 8888))

def handle_client(client_socket):
    try:
        request_line = client_socket.recv(BUFFER_SIZE).decode()
        if not request_line:
            client_socket.close()
            return

        method, url, _ = request_line.split(' ', 2)

        if method == 'CONNECT':
            host_port = url.split(':')
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 443

            remote_socket = socket.create_connection((host, port))
            client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            tunnel(client_socket, remote_socket)
        else:
            parts = url.split('/', 3)
            if url.startswith('http://'):
                host_port = parts[2].split(':')
                host = host_port[0]
                port = int(host_port[1]) if len(host_port) > 1 else 80
                path = '/' + parts[3] if len(parts) > 3 else '/'
            else:
                client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                client_socket.close()
                return

            remote_socket = socket.create_connection((host, port))
            remote_socket.sendall(f"{method} {path} HTTP/1.0\r\n".encode())

            while True:
                line = client_socket.recv(BUFFER_SIZE)
                remote_socket.sendall(line)
                if line in (b'\r\n', b'\n', b''):
                    break

            tunnel(client_socket, remote_socket)
    except Exception as e:
        print(f"[ERROR] {e}")
        client_socket.close()

def tunnel(sock1, sock2):
    sockets = [sock1, sock2]
    while True:
        r, _, _ = select.select(sockets, [], [])
        if sock1 in r:
            data = sock1.recv(BUFFER_SIZE)
            if not data:
                break
            sock2.sendall(data)
        if sock2 in r:
            data = sock2.recv(BUFFER_SIZE)
            if not data:
                break
            sock1.sendall(data)
    sock1.close()
    sock2.close()

def start_proxy():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', LISTEN_PORT))
    server_socket.listen(100)
    print(f"Proxy server running on port {LISTEN_PORT}")
    while True:
        client_socket, _ = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()

if __name__ == '__main__':
    start_proxy()
