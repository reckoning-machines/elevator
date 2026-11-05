"""Run the demo server: ``python -B -m web [--store DIR] [--port N]`` (local, no authentication, a demo surface)."""

import argparse

import uvicorn

from web.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -B -m web")
    parser.add_argument("--store", help="a Store (see `store init`) for explicit checkpoint and reopen")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(create_app(store=args.store), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
