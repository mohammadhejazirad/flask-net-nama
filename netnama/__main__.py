import argparse
import os
import signal

from waitress.server import create_server
from netnama import create_app


def main():
    parser = argparse.ArgumentParser(description="NetNama single-process network toolbox")
    parser.add_argument("--host", default=os.getenv("NETNAMA_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("NETNAMA_PORT", "8080")))
    args = parser.parse_args()
    public = os.getenv("NETNAMA_MODE", "local") == "public"
    if not public and args.host not in ("127.0.0.1", "::1", "localhost"):
        parser.error("Non-loopback binding requires NETNAMA_MODE=public.")
    app = create_app()
    server = create_server(
        app,
        host=args.host,
        port=args.port,
        threads=24,
        max_request_body_size=1150000,
        inbuf_overflow=2 * 1024 * 1024,
        outbuf_overflow=32 * 1024 * 1024,
        outbuf_high_watermark=2 * 1024 * 1024,
        channel_timeout=75,
        clear_untrusted_proxy_headers=True,
    )

    def shutdown(*_):
        app.extensions["scheduler"].close()
        server.close()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        print(f"NetNama: http://{args.host}:{args.port} — execution origin: server", flush=True)
        server.run()
    finally:
        app.extensions["scheduler"].close()


if __name__ == "__main__":
    main()
