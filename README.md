# 🌐 Distributed Multi-Server Chat & Shared Logging System

A fully functional **distributed chat application** inspired by platforms like Discord.  
Built for academic purposes in the **Distributed & Cloud Computing** course, this system demonstrates:

- Distributed server clustering  
- Inter-server message forwarding  
- Client–server communication  
- Shared logging with synchronization  
- Fault tolerance and recovery  

Multiple servers work together to form a chat network where clients can connect anywhere and still receive messages from the entire cluster.

---

## ✨ Key Features

- 🖧 **Multi-server chat cluster** (Server A, B, C…)
- 🔁 **Direct Relay / Full-Mesh topology** (star)  
- 💬 **Local broadcast and global message forwarding**
- 📝 **Shared log file** for all servers
- 🔐 **Mutex-protected logging**  
  - Works on **Windows** (`msvcrt`)  
  - Works on **Linux/macOS** (`fcntl`)
- ⚠️ **Fault tolerant architecture**
- 📡 **JSON-based communication protocol**

---

## 🧩 System Architecture

```

Clients → Server Node → Relay Network → Shared Log

```

### How messages flow:
1. A client connects to any server.
2. Client sends message → server broadcasts locally.
3. The server relays the message to all other servers.
4. Other servers broadcast to their own clients.
5. All servers append the message to **one shared log file**.

---

## ⭐ Server Topology (Implemented)

The system uses a **Star / Direct-Relay (Full Mesh)** topology.

```

```
  [ Server B ]
     /   \
    /     \
```

[ Server A ]–[ Server C ]

````

### Why Full-Mesh?
- Simple implementation  
- Fast message delivery  
- No hops or routing complexity  
- More resilient to node failures  
- Perfect for small academic clusters (2–10 servers)

---

## 📡 JSON Message Protocol

### Client → Server
```json
{"type":"login","username":"Dana"}
{"type":"msg","text":"Hello everyone!"}
{"type":"quit"}
````

### Server → Client

```json
{"type":"system","text":"Welcome Dana to Server A"}
{"type":"msg","from":"Dana","server":"A","text":"Hello everyone!"}
{"type":"error","text":"username taken"}
```

### Server ↔ Server (Relay)

```json
{
  "type":"relay_msg",
  "from":"Dana",
  "origin_server":"A",
  "text":"Hello from A",
  "timestamp": 1732199912
}
```

---

## 📁 Project Structure

```
Distributed-Multi-Server-Chat-Logging-System/
│
├── server/
│   ├── server.py          # Main server node with relay logic
│   ├── logger.py          # Shared logger with cross-platform mutex
│   ├── peersA.json        # Peer config for Server A
│   ├── peersB.json        # Peer config for Server B
│   └── peersC.json        # Peer config for Server C
│
├── client/
│   └── client.py          # Console-based chat client
│
├── shared/
│   └── logs/
│       └── chat.log       # Auto-created shared log
│
└── README.md
```

---

## ⚙️ Requirements

* Python **3.8+**
* Works on:

  * 🪟 Windows
  * 🐧 Linux
  * 🍎 macOS
* No external pip packages needed (pure Python)

---

# 🚀 Running the Project

## 1️⃣ Start the Servers (3 terminals)

### **Server A**

```bash
cd server
python server.py A 0.0.0.0 5001 ../shared/logs/chat.log peersA.json
```

### **Server B**

```bash
cd server
python server.py B 0.0.0.0 5002 ../shared/logs/chat.log peersB.json
```

### **Server C**

```bash
cd server
python server.py C 0.0.0.0 5003 ../shared/logs/chat.log peersC.json
```

---

## 2️⃣ Start the Clients (3 terminals)

### Client → Server A

```bash
cd client
python client.py 127.0.0.1 5001 Dana
```

### Client → Server B

```bash
python client.py 127.0.0.1 5002 Ahmad
```

### Client → Server C

```bash
python client.py 127.0.0.1 5003 Lina
```

---

# 🧪 Testing Checklist

### ✔ Local Message Broadcast

Send message from a client on Server A →
Only A's local users should see it.

### ✔ Inter-Server Forwarding

Write something on Server A →
Clients on Servers B and C should also receive it.

### ✔ Shared Logging

Open:

```
shared/logs/chat.log
```

You should see JSON-formatted entries from all servers.

### ✔ Fault Tolerance Test

1. Kill Server B
2. Servers A and C continue working
3. Restart Server B
4. It reconnects automatically
5. Inter-server messages resume

---

# 🔒 Logging & Synchronization

### Shared Log File

```
shared/logs/chat.log
```

### Mutex-based Sync

* Windows → `msvcrt.locking()`
* Linux/macOS → `fcntl.flock()`

Ensures:

* No corrupted logs
* Safe concurrent write operations
* Consistent chronological logging

---

# 👥 Team Responsibilities

| Student | Responsibility                                    |
| ------- | ------------------------------------------------- |
| **1**   | Server cluster architecture + relay protocol      |
| **2**   | Client interface (connection, sending, receiving) |
| **3**   | Logging system + synchronization (mutex)          |

---

# 🎬 Presentation Scenario

To impress your professor, present:

1. **Three servers running** simultaneously
2. **Three clients connected** to different servers
3. A message typed on Server A reaching B and C
4. Open `chat.log` → show synchronized logging
5. Kill a server → show cluster resilience
6. Restart the server → show auto-reconnect

---

# 🚧 Future Improvements

* Switchable topologies (Bus / Ring)
* Private chats / rooms
* Load balancing
* WebSocket client interface
* Docker & Kubernetes deployment
* Message history retrieval

---

# 📜 License

This project is developed for academic and educational purposes.
Feel free to fork and modify for learning or research.


```
