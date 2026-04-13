"""Plot helpers for the TCP sliding-window demo.

Each function takes parallel lists (times, values) and writes a PNG.
Callers should already downsample before passing big series — for 10M
packets, keep samples under ~10k points or rendering is painful.
"""

import matplotlib

matplotlib.use("Agg")  # headless: don't require a display
import matplotlib.pyplot as plt


def plot_window(times, values, path, title, label):
    """Single-line window plot (packets vs time)."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(times, values, label=label, linewidth=1)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Packets")
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_seq_scatter(times, seqs, path, title, color):
    """Scatter of sequence number against time."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.scatter(times, seqs, s=2, c=color, alpha=0.5)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Packet number")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
