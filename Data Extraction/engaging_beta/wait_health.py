"""Block until a vLLM /health endpoint answers 200 (weights loaded, server
ready) or the timeout expires. Usage:
    python wait_health.py --url http://127.0.0.1:8000/health --timeout 1800
"""
import argparse
import sys
import time
import urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--interval", type=int, default=15)
    args = ap.parse_args()

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(args.url, timeout=10) as resp:
                if resp.status == 200:
                    print(f"[wait_health] server ready after "
                          f"{args.timeout - int(deadline - time.time())}s")
                    return
        except Exception:
            pass
        time.sleep(args.interval)
    sys.exit(f"[wait_health] server not healthy after {args.timeout}s")


if __name__ == "__main__":
    main()
