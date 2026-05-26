import datetime
import sys


def log(msg: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True, file=sys.stdout)


sys.stdout.reconfigure(encoding="utf-8", errors="replace")
