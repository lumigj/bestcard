import argparse

from bestcard.api.app import run as run_api
from bestcard.integrations.telegram_bot import main as run_bot
from bestcard.rag.ingest import main as run_ingest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BestCard unified entrypoint")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["api", "bot", "ingest"],
        default="api",
        help="Run mode: api (default), bot, ingest",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.mode == "api":
        run_api()
        return

    if args.mode == "bot":
        run_bot()
        return

    run_ingest()


if __name__ == "__main__":
    main()
