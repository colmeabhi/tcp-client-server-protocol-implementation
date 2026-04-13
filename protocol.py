import logging
import sys
from datetime import datetime

PORT = 5001
MAX_SEQ = 1 << 16
DONE_SIG = 0xFFFFFFFF


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
