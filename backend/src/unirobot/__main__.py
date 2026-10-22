"""Run the task console gateway."""

from __future__ import annotations

import argparse
import os


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uniRobotPlatform task console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--catalog", default=None)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)
    if args.catalog:
        os.environ["UNIROBOT_CATALOG"] = args.catalog

    import uvicorn

    uvicorn.run(
        "unirobot.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
