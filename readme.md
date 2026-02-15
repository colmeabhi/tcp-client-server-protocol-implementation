# TCP Sliding Window Protocol

A TCP-based sliding window protocol implementation with simulated packet drops and retransmission.

## How to Run

### Local Testing (via ngrok)

1. Start ngrok:
   ```bash
   ngrok tcp 5001
   ```

2. Update `SERVER_HOST` and `SERVER_PORT` in `client.py` with the ngrok forwarding address.

3. Run server (terminal 1):
   ```bash
   python server.py
   ```

4. Run client (terminal 2):
   ```bash
   python client.py
   ```

### Remote Testing

Same steps — just run the server + ngrok on one machine and the client on the other.

## Parameters

| Parameter | Value |
|-----------|-------|
| Total packets | 1,000 |
| Max sequence number | 2^16 (65,536) |
| Window size | 256 |
| Drop probability | 1% |
| Retransmit interval | Every 100 packets |
| Goodput report interval | Every 1,000 packets received |

## Protocol Flow

```
CLIENT                        SERVER
  |--- "network" ------------>|
  |<-- "success" -------------|
  |--- [pkt_no, seq_no] ----->|  (8 bytes per packet)
  |<-- [ACK = seq_no + 1] ----|
  |        ... repeat ...     |
  |--- [DONE_SIG, total] ---->|
```

## Output (Server)

Reports unique packets received, missing packets, and average goodput at the end of transmission.
