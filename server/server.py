# server.py
import socket
import threading
import json
import time
import sys
from logger import SharedLogger


# ----------------- Helpers -----------------

def send_json(sock: socket.socket, obj: dict):
    """
    Send one JSON message ending with newline.
    """
    data = (json.dumps(obj) + "\n").encode("utf-8")
    sock.sendall(data)


def recv_json_lines(sock: socket.socket):
    """
    Generator that yields JSON-decoded messages line-by-line.
    """
    buffer = ""
    while True:
        data = sock.recv(4096)
        if not data:
            return

        buffer += data.decode("utf-8")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line:
                yield json.loads(line)


# ----------------- Server Class -----------------

class ChatServer:
    """
    A server node in the cluster:
    - Accepts client TCP connections
    - Accepts peer server connections
    - Broadcasts locally
    - Forwards inter-server messages
    - Logs to shared file with mutex
    """

    def __init__(self, server_id, host, port, peers, logfile):

        self.server_id = server_id
        self.host = host
        self.port = port

        # peers: list of (peer_id, host, port)
        self.peers = peers

        # shared logger (mutex protected)
        self.logger = SharedLogger(logfile)

        # connected clients dictionary: username -> socket
        self.clients = {}
        self.clients_lock = threading.Lock()

        # connected peers dictionary: peer_id -> socket
        self.peer_sockets = {}
        self.peer_lock = threading.Lock()

        # seen relay messages to avoid loops
        self.seen = set()
        self.seen_lock = threading.Lock()


    # ----------------- Client Side -----------------

    def handle_client(self, csock, first_msg=None):
        """
        Handles a client after connection.
        first_msg is used if we already read first line in router.
        """
        username = None

        try:
            # If we already got first message, handle it first
            if first_msg:
                msgs_iter = iter([first_msg])
            else:
                msgs_iter = recv_json_lines(csock)

            for msg in msgs_iter:
                msg_type = msg.get("type")

                # LOGIN
                if msg_type == "login":
                    requested_name = msg.get("username", "").strip()

                    if not requested_name:
                        send_json(csock, {"type": "error", "text": "username required"})
                        continue

                    with self.clients_lock:
                        if requested_name in self.clients:
                            send_json(csock, {"type": "error", "text": "username taken"})
                            continue

                        self.clients[requested_name] = csock
                        username = requested_name

                    send_json(csock, {
                        "type": "system",
                        "text": f"Welcome {username}! Connected to Server {self.server_id}"
                    })

                    self.broadcast_local({
                        "type": "system",
                        "text": f"{username} joined the chat"
                    }, exclude=username)


                # MESSAGE
                elif msg_type == "msg" and username:
                    text = msg.get("text", "")

                    record = {
                        "type": "msg",
                        "from": username,
                        "server": self.server_id,
                        "text": text,
                        "timestamp": time.time()
                    }

                    # broadcast local users
                    self.broadcast_local(record)

                    # forward to peers
                    self.forward_to_peers(record)

                    # log (mutex protected)
                    self.logger.log(record)


                # QUIT
                elif msg_type == "quit":
                    break

                else:
                    send_json(csock, {"type": "error", "text": "invalid request"})

            # continue reading remaining lines normally
            for msg in recv_json_lines(csock):
                # re-run same logic
                msg_type = msg.get("type")

                if msg_type == "msg" and username:
                    text = msg.get("text", "")

                    record = {
                        "type": "msg",
                        "from": username,
                        "server": self.server_id,
                        "text": text,
                        "timestamp": time.time()
                    }

                    self.broadcast_local(record)
                    self.forward_to_peers(record)
                    self.logger.log(record)

                elif msg_type == "quit":
                    break

        except:
            pass

        finally:
            if username:
                with self.clients_lock:
                    self.clients.pop(username, None)

                self.broadcast_local({
                    "type": "system",
                    "text": f"{username} left the chat"
                })

            csock.close()


    def broadcast_local(self, record, exclude=None):
        """
        Broadcast message to all local users on this server.
        """
        dead = []

        with self.clients_lock:
            for uname, sock in self.clients.items():
                if uname == exclude:
                    continue
                try:
                    send_json(sock, record)
                except:
                    dead.append(uname)

            # remove dead sockets
            for uname in dead:
                self.clients.pop(uname, None)



    # ----------------- Peer / Relay Side -----------------

    def connect_to_peers(self):
        """
        Tries to connect to every peer server in background threads.
        If peer down, keeps retrying (failure-safe).
        """
        for pid, phost, pport in self.peers:
            t = threading.Thread(
                target=self.peer_connector,
                args=(pid, phost, pport),
                daemon=True
            )
            t.start()


    def peer_connector(self, pid, phost, pport):
        """
        Connects to a peer server and keeps retrying if it fails.
        """
        while True:
            try:
                psock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                psock.connect((phost, pport))

                # handshake
                send_json(psock, {"type": "hello", "from_server": self.server_id})

                with self.peer_lock:
                    self.peer_sockets[pid] = psock

                # listen to peer messages
                threading.Thread(
                    target=self.handle_peer,
                    args=(pid, psock),
                    daemon=True
                ).start()

                return  # connected successfully

            except:
                time.sleep(2)  # retry after delay


    def handle_peer(self, pid, psock):
        """
        Receives relay messages from peer server.
        """
        try:
            for msg in recv_json_lines(psock):

                if msg.get("type") != "relay_msg":
                    continue

                key = (
                    msg.get("origin_server"),
                    msg.get("timestamp"),
                    msg.get("from"),
                    msg.get("text")
                )

                # dedupe to avoid infinite loops
                with self.seen_lock:
                    if key in self.seen:
                        continue
                    self.seen.add(key)

                # convert relay to local broadcast record
                local_record = {
                    "type": "msg",
                    "from": msg["from"],
                    "server": msg["origin_server"],
                    "text": msg["text"],
                    "timestamp": msg["timestamp"]
                }

                # broadcast to local clients
                self.broadcast_local(local_record)

                # log message
                self.logger.log(local_record)

        except:
            pass
        finally:
            with self.peer_lock:
                self.peer_sockets.pop(pid, None)
            psock.close()


    def forward_to_peers(self, record):
        """
        Send message to all peers.
        If relay fails -> only inter-server messages stop,
        local still works (requirement).
        """
        relay_packet = {
            "type": "relay_msg",
            "from": record["from"],
            "origin_server": record["server"],
            "text": record["text"],
            "timestamp": record["timestamp"]
        }

        with self.peer_lock:
            for pid, psock in list(self.peer_sockets.items()):
                try:
                    send_json(psock, relay_packet)
                except:
                    self.peer_sockets.pop(pid, None)



    # ----------------- Router for New Connections -----------------

    def route_connection(self, sock):
        """
        First message decides if this socket is a peer or client.
        """
        try:
            first_msg = next(recv_json_lines(sock))

            if first_msg.get("type") == "hello":
                pid = first_msg.get("from_server")

                with self.peer_lock:
                    self.peer_sockets[pid] = sock

                self.handle_peer(pid, sock)

            else:
                self.handle_client(sock, first_msg=first_msg)

        except:
            sock.close()


    # ----------------- Main Server Loop -----------------

    def serve_forever(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((self.host, self.port))
        lsock.listen()

        print(f"[Server {self.server_id}] running on {self.host}:{self.port}")

        # connect to peers in background
        self.connect_to_peers()

        while True:
            sock, addr = lsock.accept()
            threading.Thread(
                target=self.route_connection,
                args=(sock,),
                daemon=True
            ).start()



# ----------------- Run -----------------

if __name__ == "__main__":
    """
    Example:
      python server.py A 0.0.0.0 5001 shared/logs/chat.log peersA.json

    peersA.json format:
      [
        ["B","127.0.0.1",5002],
        ["C","127.0.0.1",5003]
      ]
    """

    if len(sys.argv) < 6:
        print("Usage: python server.py <ID> <HOST> <PORT> <LOGFILE> <PEERS.json>")
        sys.exit(1)

    sid = sys.argv[1]
    host = sys.argv[2]
    port = int(sys.argv[3])
    logfile = sys.argv[4]
    peers_file = sys.argv[5]

    with open(peers_file, "r", encoding="utf-8") as f:
        peers = json.load(f)

    server = ChatServer(sid, host, port, peers, logfile)
    server.serve_forever()
