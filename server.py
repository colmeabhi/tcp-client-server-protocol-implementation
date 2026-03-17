import socket
import struct

HOST = "0.0.0.0"
PORT = 5001
MAX_SEQ = 1 << 16  # 2^16 = 65,536
GOODPUT_IN = 1_000  # report goodput every N received packets
DONE_SIG = 0xFFFFFFFF  # end-of-transmission sentinel


def run_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[SERVER] Listening on port {PORT} ...")

    conn, addr = srv.accept()
    print(f"[SERVER] Connected to {addr}")

    # --- Handshake ---
    length = struct.unpack("!H", conn.recv(2))[0]
    init_str = conn.recv(length).decode()
    print(f"[SERVER] Received: '{init_str}'")

    reply = b"success"
    conn.sendall(struct.pack("!H", len(reply)) + reply)
    print("[SERVER] Sent: 'success'\n[SERVER] Receiving packets ...\n")

    # --- State ---
    received = set()
    n_recv = 0
    total_sent = 0
    goodput_samples = []

    # --- Receive loop ---
    while True:
        data = conn.recv(8)
        if len(data) < 8:
            break

        pkt_no, seq_no = struct.unpack("!II", data)

        if pkt_no == DONE_SIG:
            total_pkts = seq_no  # unique packets the client attempted
            break

        # Track unique received packets
        if pkt_no not in received:
            received.add(pkt_no)
            n_recv += 1

        # Send ACK = seq_no + 1
        conn.sendall(struct.pack("!I", seq_no + 1))

        # Report goodput every GOODPUT_IN packets
        if n_recv % GOODPUT_IN == 0 and n_recv > 0:
            # goodput = received / attempted so far (pkt_no+1 = packets attempted)
            goodput = n_recv / (pkt_no + 1)
            goodput_samples.append(goodput)
            print(
                f"  [{n_recv:>9,} recv / ~{pkt_no + 1:>9,} attempted]  "
                f"goodput = {goodput:.5f}"
            )

    # --- Final report ---
    missing = total_pkts - n_recv
    avg_gp = sum(goodput_samples) / len(goodput_samples) if goodput_samples else 0

    print("\n[SERVER] ═══════════ FINAL RESULTS ═══════════")
    print(f"  Total packets attempted  : {total_pkts:>12,}")
    print(f"  Packets received         : {n_recv:>12,}")
    print(f"  Missing packets          : {missing:>12,}")
    print(f"  Average goodput          : {avg_gp:.6f}")
    print("[SERVER] ══════════════════════════════════════")

    conn.close()
    srv.close()


if __name__ == "__main__":
    run_server()
