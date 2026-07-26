# TCP Sliding Window Protocol

A simple TCP sliding window protocol with simulated packet drops and retransmission.
Sends 10 million packets from client to server, drops 1% on purpose, and retransmits until everything is delivered.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## How to Run

You need two terminals (or two machines): one for the server, one for the client.

### Option 1: Same machine

Leave `SERVER_HOST = "127.0.0.1"` in `client.py`.

```bash
# terminal 1
python server.py

# terminal 2
python client.py
```

### Option 2: Two machines on the same WiFi

On the server machine, find its LAN IP:

```bash
ipconfig getifaddr en0      # macOS
```

On the client machine, set `SERVER_HOST` in `client.py` to that IP.

```bash
# server machine
python server.py

# client machine
python client.py
```

### Option 3: Over the internet (ngrok)

```bash
ngrok tcp 5001
```

Copy the forwarding address into `SERVER_HOST` and `SERVER_PORT` in `client.py`, then run server and client as above.

## Parameters

| Parameter | Value |
|-----------|-------|
| Total packets | 10,000,000 |
| Packet frame | 12 bytes (`!III` = pkt_no, seq_no, attempts) |
| Max sequence number | 2^16 (65,536) |
| Window size | 256 |
| Drop probability | 1% |
| Retransmit interval | Every 100 new packets (or when window stalls) |
| Goodput report interval | Every 1,000 packets received |

## Protocol Flow

```
CLIENT                                 SERVER
  |--- "network" -------------------->|
  |<-- "success" ---------------------|
  |--- [pkt_no, seq_no, attempts] -->|  (12 bytes per packet)
  |<-- [ACK = seq_no + 1] ------------|
  |         ... repeat ...            |
  |--- [DONE_SIG, total, attempts] ->|
```

## Output

Each side writes its own log file and plots:

**Client** (`client.py`)
- `client_log.txt` — progress, retransmission distribution
- `plot_sender_window.png` — in-flight packets over time
- `plot_seq_dropped.png` — sequence numbers dropped over time

**Server** (`server.py`)
- `server_log.txt` — goodput reports, final results
- `plot_receiver_window.png` — out-of-order buffer size over time
- `plot_seq_received.png` — sequence numbers received over time

Run the client and server on separate machines and each side generates only its own plots.
