"""Block until OUR vLLM server is ready, or the timeout expires.

Usage:
    python wait_health.py --base http://127.0.0.1:8123 --model qwen35-122b-fp8 \
                          --timeout 1800

Why this is not just a /health ping (2026-07-29, round 3): the sbatch hardcoded
port 8000, another user's service already held that port on the node, our vLLM
died with `OSError: [Errno 98] Address already in use`, and a bare /health check
connected to THEIR server and reported "ready after 1s". All 186 extraction
calls were then sent to a stranger's endpoint and rejected with HTTP 401.

So readiness now means: the endpoint answers AND it is serving the model we
asked for. Anything else is treated as "not ours" and fails loudly rather than
silently borrowing whatever happens to be listening.
"""
import argparse
import json
import sys
import time
import urllib.request


def _get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True,
                    help="server root, e.g. http://127.0.0.1:8123")
    ap.add_argument("--model", required=True,
                    help="the --served-model-name we booted; the server must report it")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--interval", type=int, default=15)
    args = ap.parse_args()

    base = args.base.rstrip("/")
    start = time.time()
    deadline = start + args.timeout
    last = ""
    while time.time() < deadline:
        try:
            status, _ = _get(f"{base}/health")
            if status == 200:
                # identity check: is this OUR model, or someone else's server?
                mstatus, body = _get(f"{base}/v1/models")
                names = [m.get("id") for m in json.loads(body).get("data", [])]
                if args.model in names:
                    print(f"[wait_health] {args.model} ready after "
                          f"{int(time.time() - start)}s at {base}")
                    return
                last = (f"port answered but serves {names!r}, not "
                        f"{args.model!r} - NOT our server")
                sys.exit(f"[wait_health] ABORT: {last}")
        except SystemExit:
            raise
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(args.interval)
    sys.exit(f"[wait_health] {args.model} not ready after {args.timeout}s "
             f"(last: {last})")


if __name__ == "__main__":
    main()
