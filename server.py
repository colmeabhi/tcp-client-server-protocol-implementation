import socket
import struct
import time

from plots import plot_seq_scatter, plot_window
from protocol import DONE_SIG, PORT, recv_exact, setup_logger

HOST = "0.0.0.0"
GOODPUT_IN = 1_000  # report goodput every N received packets
LOG_PATH = "server_log.txt"

# Plot sampling: one receiver-window sample per N received packets,
# and keep every Kth received packet for the scatter.
WINDOW_SAMPLE_EVERY = 500
RECV_KEEP_EVERY = 500

log = setup_logger("server", LOG_PATH).info


def run_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    log(f"[SERVER] Listening on port {PORT} ...")

    conn, addr = srv.accept()
    log(f"[SERVER] Connected to {addr}")

    # --- Handshake ---
    length = struct.unpack("!H", recv_exact(conn, 2))[0]
    init_str = recv_exact(conn, length).decode()
    log(f"[SERVER] Received: '{init_str}'")

    reply = b"success"
    conn.sendall(struct.pack("!H", len(reply)) + reply)
    log("[SERVER] Sent: 'success'")
    log("[SERVER] Receiving packets ...")

    # --- State ---
    received = set()          # set of all received pkt_nos
    n_recv = 0                # count of unique packets received
    total_attempted = 0       # total attempts by client (sent + dropped)
    next_expected = 0         # next contiguous seq number expected
    missing = set()           # currently missing sequence numbers
    goodput_samples = []

    # --- Plot samples (server-side only) ---
    t0 = time.perf_counter()
    window_times = []         # seconds since t0
    receiver_window = []      # size of missing/out-of-order buffer at sample time
    recv_times = []           # time of each kept receive event
    recv_pkts = []            # pkt_no of each kept receive event

    # --- Receive loop ---
    while True:
        data = recv_exact(conn, 12)
        pkt_no, seq_no, attempted = struct.unpack("!III", data)

        if pkt_no == DONE_SIG:
            total_pkts = seq_no       # total unique packets client attempted
            total_attempted = attempted
            break

        total_attempted = attempted   # latest cumulative attempt count from client

        # Track unique received packets
        if pkt_no not in received:
            received.add(pkt_no)
            n_recv += 1

            # Remove from missing if it was there (retransmit arrived)
            missing.discard(pkt_no)

            # Update contiguous tracking: add any gaps to missing set
            if pkt_no >= next_expected:
                for gap in range(next_expected, pkt_no):
                    if gap not in received:
                        missing.add(gap)
                next_expected = max(next_expected, pkt_no + 1)

            # Sample for plots
            if n_recv % RECV_KEEP_EVERY == 0:
                recv_times.append(time.perf_counter() - t0)
                recv_pkts.append(pkt_no)
            if n_recv % WINDOW_SAMPLE_EVERY == 0:
                window_times.append(time.perf_counter() - t0)
                receiver_window.append(len(missing))

        # Send ACK = seq_no + 1
        conn.sendall(struct.pack("!I", seq_no + 1))

        # Report goodput every GOODPUT_IN unique packets
        if (
            n_recv % GOODPUT_IN == 0
            and n_recv > 0
            and n_recv // GOODPUT_IN == len(goodput_samples) + 1
        ):
            goodput = n_recv / total_attempted
            goodput_samples.append(goodput)
            log(
                f"  [{n_recv:>12,} recv / {total_attempted:>12,} attempted]  "
                f"goodput = {goodput:.5f}  missing = {len(missing)}"
            )

    # --- Final report ---
    avg_gp = sum(goodput_samples) / len(goodput_samples) if goodput_samples else 0

    log("")
    log("[SERVER] ═══════════ FINAL RESULTS ═══════════")
    log(f"  Total packets attempted  : {total_attempted:>12,}")
    log(f"  Total unique attempted   : {total_pkts:>12,}")
    log(f"  Unique packets received  : {n_recv:>12,}")
    log(f"  Missing packets          : {len(missing):>12,}")
    log(f"  Average goodput          : {avg_gp:.6f}")
    if missing and len(missing) <= 20:
        log(f"  Missing seq numbers      : {sorted(missing)}")
    log("[SERVER] ══════════════════════════════════════")

    conn.close()
    srv.close()

    plot_window(
        window_times, receiver_window,
        "plot_receiver_window.png",
        "TCP receiver window (out-of-order buffer) over time",
        label="Receiver window",
    )
    plot_seq_scatter(
        recv_times, recv_pkts,
        "plot_seq_received.png",
        "TCP sequence numbers received over time",
        color="tab:blue",
    )
    log("[SERVER] Saved plots: plot_receiver_window.png, plot_seq_received.png")


if __name__ == "__main__":
    run_server()
