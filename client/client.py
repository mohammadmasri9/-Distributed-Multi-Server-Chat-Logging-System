# client.py
import socket
import threading
import json
import sys


def send_json(sock, obj):
    """Send JSON message with newline terminator."""
    data = (json.dumps(obj) + "\n").encode("utf-8")
    sock.sendall(data)


def recv_json_lines(sock):
    """Receive JSON messages line-by-line."""
    buffer = ""
    while True:
        data = sock.recv(4096)
        if not data:
            return
        
        buffer += data.decode("utf-8")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line.strip():
                yield json.loads(line)


def listener(sock):
    """Background thread that prints incoming server messages."""
    try:
        for msg in recv_json_lines(sock):
            msg_type = msg.get("type")

            if msg_type == "msg":
                print(f"[{msg['server']}] {msg['from']}: {msg['text']}")
            else:
                # system messages, errors, joined/left notifications
                print(f"* {msg.get('text')}")
    except:
        print("Disconnected from server.")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python client.py <IP> <PORT> <USERNAME>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]

    # Connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    # Send login request
    send_json(sock, {"type": "login", "username": username})

    # Start listener thread
    threading.Thread(target=listener, args=(sock,), daemon=True).start()

    print(f"Connected as {username}. Type messages:")
    print("Type /quit to exit.\n")

    try:
        while True:
            text = input()

            if text.strip().lower() == "/quit":
                send_json(sock, {"type": "quit"})
                break

            send_json(sock, {"type": "msg", "text": text})

    finally:
        sock.close()
