import random
import socket
import struct

SERVER_HOST = "6.tcp.us-cal-1.ngrok.io"  # ← change to server machine's IP
SERVER_PORT = 19359
MAX_SEQ = 1 << 16  # 2^16 = 65,536
TOTAL_PKTS = 1000  # total packets to send
WINDOW_SIZE = 256  # sliding window size
DROP_PROB = 0.01  # 1% drop probability
RETRANS_INT = 100  # retransmit dropped pkts every N new packets
DONE_SIG = 0xFFFFFFFF  # end-of-transmission sentinel


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))
    print(f"[CLIENT] Connected to {SERVER_HOST}:{SERVER_PORT}")

    # --- Handshake ---
    init = b"network"
    sock.sendall(struct.pack("!H", len(init)) + init)

    length = struct.unpack("!H", sock.recv(2))[0]
    reply = sock.recv(length).decode()
    print(f"[CLIENT] Server replied: '{reply}'")
    if reply != "success":
        print("[CLIENT] Handshake failed. Exiting.")
        return

    # --- State ---
    dropped_queue = []  # pkt_nos that were dropped, queued for retransmit
    total_sent = 0
    new_pkt_count = 0  # counts toward next RETRANS_INT trigger
    base = 0  # sliding window base

    print(f"[CLIENT] Sending {TOTAL_PKTS:,} packets ...\n")

    # --- Sliding window loop ---
    while base < TOTAL_PKTS:
        wnd_end = min(base + WINDOW_SIZE, TOTAL_PKTS)

        # Send each packet in the window
        for pkt_no in range(base, wnd_end):
            seq_no = pkt_no % MAX_SEQ

            if random.random() < DROP_PROB:
                # Simulate drop — queue for retransmission
                dropped_queue.append(pkt_no)
            else:
                sock.sendall(struct.pack("!II", pkt_no, seq_no))
                sock.recv(4)  # receive ACK
                total_sent += 1

            new_pkt_count += 1

            # Retransmit dropped packets every RETRANS_INT new packets (once only)
            if new_pkt_count >= RETRANS_INT and dropped_queue:
                for dp in dropped_queue:
                    ds = dp % MAX_SEQ
                    if random.random() >= DROP_PROB:  # 99% succeed
                        sock.sendall(struct.pack("!II", dp, ds))
                        sock.recv(4)  # receive ACK
                        total_sent += 1
                    # if dropped again — permanently lost, not re-queued
                dropped_queue = []
                new_pkt_count = 0

        # Slide the window forward
        base = wnd_end

    # Signal end of transmission (TOTAL_PKTS = unique packets attempted)
    sock.sendall(struct.pack("!II", DONE_SIG, TOTAL_PKTS))

    print(f"[CLIENT] Done. Total transmissions (incl. retx): {total_sent:,}")
    sock.close()


if __name__ == "__main__":
    main()
