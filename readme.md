# CS 258 — TCP Sliding Window Protocol

---

## How to Run

**Machine 1 — Server (run first)**
```bash
python3 server.py
```

**Machine 2 — Client**  
Edit `SERVER_HOST` in `client.py` to the server's IP, then:
```bash
python3 client.py
```

> For local testing, leave `SERVER_HOST = '127.0.0.1'` and run both in separate terminals.

---

## Parameters

| Parameter | Value |
|-----------|-------|
| Total packets | 10,000,000 |
| Max sequence number | 2¹⁶ = 65,536 |
| Window size | 256 |
| Drop probability | 1% |
| Retransmit interval | Every 100 packets |
| Goodput report interval | Every 1,000 packets received |

---

## Protocol Flow

```
CLIENT                        SERVER
  |--- "network" ------------>|
  |<-- "success" -------------|
  |--- [pkt_no, seq_no] ----->|  (8 bytes per packet)
  |<-- [ACK = seq_no + 1] ----|
  |        ... 10M packets ...|
  |--- [DONE_SIG, total] ---->|
```

---

## Output (Server)
```
  [    1,000 recv / ~    1,010 sent]  goodput = 0.99010
  [    2,000 recv / ~    2,018 sent]  goodput = 0.99108
  ...
  Packets sent by client :   10,098,443
  Packets received       :    9,999,012
  Missing packets        :       99,431
  Average goodput        : 0.990183
```
