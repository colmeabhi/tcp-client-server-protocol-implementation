import logging
import random
import socket
import struct
import sys
import time
from collections import Counter, deque
from datetime import datetime

from plots import plot_seq_scatter, plot_window

SERVER_HOST = "10.0.0.162"  # change to server's IP or ngrok address
SERVER_PORT = 5001  # change to match server/ngrok port
TOTAL_PKTS = 10_000_000  # 10 million packets
WINDOW_SIZE = 256  # sliding window size
DROP_PROB = 0.01  # 1% drop probability
RETRANS_INT = 100  # retransmit dropped packets every N sequence numbers
MAX_SEQ = 1 << 16  # 2^16 = 65,536
DONE_SIG = 0xFFFFFFFF  # end-of-transmission sentinel
LOG_PATH = "client_log.txt"

# Plot sampling: keep every Kth drop event (at 1% drop, this is ~0.05% of packets).
DROP_KEEP_EVERY = 20


def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionResetError("Connection closed")
        data += chunk
    return data


def setup_logger(name, path):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")
    for h in (logging.FileHandler(path, mode="a"), logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        logger.addHandler(h)
    logger.info(f"=== Session started {datetime.now():%Y-%m-%d %H:%M:%S} ===")
    return logger


log = setup_logger("client", LOG_PATH).info


def print_attempt_distribution(attempts):
    """Print a table of (transmission count -> number of packets)."""
    if not attempts:
        return
    dist = Counter(attempts.values())
    total = sum(dist.values())
    log("")
    log("[CLIENT] ─── Transmission-count distribution ───")
    log(f"  {'Transmissions':>13}  {'Packets':>12}  {'Percent':>8}")
    for n in sorted(dist):
        pct = 100 * dist[n] / total
        log(f"  {n:>13}  {dist[n]:>12,}  {pct:>7.3f}%")
    log("[CLIENT] ──────────────────────────────────────")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))
    log(f"[CLIENT] Connected to {SERVER_HOST}:{SERVER_PORT}")

    # --- Handshake: send "network", expect "success" ---
    init = b"network"
    sock.sendall(struct.pack("!H", len(init)) + init)

    length = struct.unpack("!H", recv_exact(sock, 2))[0]
    reply = recv_exact(sock, length).decode()
    log(f"[CLIENT] Server replied: '{reply}'")
    if reply != "success":
        log("[CLIENT] Handshake failed. Exiting.")
        return

    # --- State ---
    base = 0  # left edge of the sliding window
    next_to_send = 0  # next packet number to attempt
    total_sent = 0  # packets actually transmitted
    total_attempted = 0  # total attempts (sent + dropped)
    acked = set()  # packets acked but ahead of base
    dropped = set()  # packets that were "dropped" (not sent)
    sent_queue = deque()  # send order — maps ACKs back to pkt_nos
    pkts_since_retrans = 0  # counts new packets sent since last retransmit
    last_progress = -1
    attempts = {}  # pkt_no -> number of send attempts (sent + simulated drops)

    # --- Plot samples (client-side only) ---
    t0 = time.perf_counter()
    window_times = []       # seconds since t0
    sender_window = []      # in-flight packets at sample time
    drop_times = []         # time of each kept drop event
    drop_pkts = []          # pkt_no of each kept drop event
    drop_counter = 0

    log(f"[CLIENT] Sending {TOTAL_PKTS:,} packets (window={WINDOW_SIZE})")

    # --- Sliding window loop ---
    while base < TOTAL_PKTS:
        # 1. Fill the window: send new packets while window has room
        sent_this_round = 0
        while next_to_send < min(base + WINDOW_SIZE, TOTAL_PKTS):
            total_attempted += 1
            pkts_since_retrans += 1
            attempts[next_to_send] = 1
            if random.random() < DROP_PROB:
                dropped.add(next_to_send)
                if drop_counter % DROP_KEEP_EVERY == 0:
                    drop_times.append(time.perf_counter() - t0)
                    drop_pkts.append(next_to_send)
                drop_counter += 1
            else:
                seq_no = next_to_send % MAX_SEQ
                sock.sendall(struct.pack("!III", next_to_send, seq_no, total_attempted))
                sent_queue.append(next_to_send)
                total_sent += 1
                sent_this_round += 1
            next_to_send += 1

        # 2. Retransmit dropped packets every RETRANS_INT new packets,
        #    or whenever the window is stuck (no new packets could be sent
        #    this round) — otherwise we can deadlock when a retransmission
        #    itself gets dropped.
        if dropped and (pkts_since_retrans >= RETRANS_INT or sent_this_round == 0):
            retry_list = sorted(dropped)
            for dp in retry_list:
                total_attempted += 1
                attempts[dp] += 1
                if random.random() < DROP_PROB:
                    if drop_counter % DROP_KEEP_EVERY == 0:
                        drop_times.append(time.perf_counter() - t0)
                        drop_pkts.append(dp)
                    drop_counter += 1
                    continue  # dropped again, stays in dropped set
                dropped.discard(dp)
                seq_no = dp % MAX_SEQ
                sock.sendall(struct.pack("!III", dp, seq_no, total_attempted))
                sent_queue.append(dp)
                total_sent += 1
                sent_this_round += 1
            pkts_since_retrans = 0

        # 3. Receive ACKs for all packets sent this round
        for _ in range(sent_this_round):
            recv_exact(sock, 4)
            acked_pkt = sent_queue.popleft()
            acked.add(acked_pkt)

        # 4. Slide base forward past all consecutively acked packets
        while base in acked:
            acked.discard(base)
            base += 1

        # Sample sender window size once per round
        window_times.append(time.perf_counter() - t0)
        sender_window.append(next_to_send - base)

        # Progress update every 1M packets
        milestone = base // 1_000_000
        if milestone > last_progress and base > 0:
            last_progress = milestone
            log(
                f"  [PROGRESS] {base:>12,} / {TOTAL_PKTS:,}  "
                f"sent={total_sent:,}  pending_drops={len(dropped)}"
            )

    # --- Signal end of transmission ---
    sock.sendall(struct.pack("!III", DONE_SIG, TOTAL_PKTS, total_attempted))

    log(f"[CLIENT] Done. Total transmissions (incl. retx): {total_sent:,}")
    log(f"[CLIENT] Total attempted (sent + dropped): {total_attempted:,}")
    log(f"[CLIENT] Packets still undelivered: {len(dropped)}")
    print_attempt_distribution(attempts)
    sock.close()

    plot_window(
        window_times, sender_window,
        "plot_sender_window.png",
        "TCP sender window (in-flight packets) over time",
        label="Sender window",
    )
    plot_seq_scatter(
        drop_times, drop_pkts,
        "plot_seq_dropped.png",
        "TCP sequence numbers dropped over time",
        color="tab:red",
    )
    log("[CLIENT] Saved plots: plot_sender_window.png, plot_seq_dropped.png")


if __name__ == "__main__":
    main()
