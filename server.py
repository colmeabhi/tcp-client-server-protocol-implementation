import socket
import json

HOST = "0.0.0.0"
PORT = 5001
GOODPUT_IN = 1_000  # report goodput every N received packets


def recv_line(conn, buf, encoding="utf-8"):
    while b"\n" not in buf[0]:
        chunk = conn.recv(65536)
        if not chunk:
            raise ConnectionResetError("Client closed connection")
        buf[0] += chunk
    line, buf[0] = buf[0].split(b"\n", 1)
    return line.decode(encoding).strip()


def send_line(conn, msg, encoding="utf-8"):
    conn.sendall((msg + "\n").encode(encoding))


def run_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[SERVER] Listening on port {PORT} ...")

    conn, addr = srv.accept()
    print(f"[SERVER] Connected to {addr}")

    buf = [b""]

    # --- Handshake ---
    init_str = recv_line(conn, buf)
    print(f"[SERVER] Received: '{init_str}'")

    send_line(conn, "success")
    print("[SERVER] Sent: 'success'\n[SERVER] Receiving packets ...\n")

    # --- State ---
    received = set()
    n_recv = 0
    total_attempts = 0
    frames_sent = 0
    goodput_samples = []

    # --- Receive loop ---
    try:
        while True:
            raw = recv_line(conn, buf)
            msg = json.loads(raw)

            if msg["type"] == "done":
                total_attempts = msg["total_attempts"]
                frames_sent = msg["frames_sent"]
                break

            if msg["type"] == "seq":
                seq = msg["seq"]
                total_attempts = msg.get("total_attempts", total_attempts)
                frames_sent = msg.get("frames_sent", frames_sent)

                if seq not in received:
                    received.add(seq)
                    n_recv += 1

                # Send ACK
                send_line(conn, json.dumps({"type": "ack", "ack": seq + 1}))

                # Report goodput every GOODPUT_IN packets
                if n_recv % GOODPUT_IN == 0 and n_recv > 0:
                    goodput = n_recv / total_attempts if total_attempts else 0
                    goodput_samples.append(goodput)
                    print(
                        f"  [{n_recv:>9,} recv / ~{total_attempts:>9,} attempted]  "
                        f"goodput = {goodput:.5f}"
                    )

        # Send FIN_ACK
        send_line(conn, json.dumps({"type": "fin_ack"}))

    except (ConnectionResetError, OSError) as e:
        print(f"\n[WARN] Client disconnected: {e}")

    # --- Final report ---
    missing = total_attempts - n_recv
    avg_gp = sum(goodput_samples) / len(goodput_samples) if goodput_samples else 0

    print("\n[SERVER] ═══════════ FINAL RESULTS ═══════════")
    print(f"  Total packets attempted  : {total_attempts:>12,}")
    print(f"  Frames sent by client    : {frames_sent:>12,}")
    print(f"  Packets received         : {n_recv:>12,}")
    print(f"  Missing packets          : {missing:>12,}")
    print(f"  Average goodput          : {avg_gp:.6f}")
    print("[SERVER] ══════════════════════════════════════")

    conn.close()
    srv.close()


if __name__ == "__main__":
    run_server()
