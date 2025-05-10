import socket
import threading
import select
import os

BUFFER_SIZE = 8192
LISTEN_PORT = int(os.environ.get("PORT", 8080))  # Default for local use

def handle_client(client_socket):
    try:
        request_line = client_socket.recv(BUFFER_SIZE).decode()
        if not request_line:
            client_socket.close()
            return

        method, url, _ = request_line.split(' ', 2)

        if method == 'CONNECT':
            host, port = url.split(':')
            port = int(port)
            remote_socket = socket.create_connection((host, port))
            client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            tunnel(client_socket, remote_socket)
        else:
            protocol, rest = url.split("://", 1)
            host_port_path = rest.split("/", 1)
            host_port = host_port_path[0]
            path = '/' + host_port_path[1] if len(host_port_path) > 1 else '/'

            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 80

            remote_socket = socket.create_connection((host, port))
            remote_socket.sendall(f"{method} {path} HTTP/1.1\r\n".encode())

            # Relay headers
            while True:
                header_line = client_socket.recv(BUFFER_SIZE)
                remote_socket.sendall(header_line)
                if header_line in (b'\r\n', b'\n', b''):
                    break

            tunnel(client_socket, remote_socket)

    except Exception as e:
        print(f"[Error] {e}")
        try:
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        except:
            pass
        client_socket.close()

def tunnel(client, remote):
    sockets = [client, remote]
    while True:
        read_socks, _, _ = select.select(sockets, [], [])
        for sock in read_socks:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                client.close()
                remote.close()
                return
            (remote if sock is client else client).sendall(data)

def start_proxy():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", LISTEN_PORT))
    server_socket.listen(100)
    print(f"HTTPS Proxy server running on port {LISTEN_PORT}")
    while True:
        client_socket, _ = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    start_proxy()
