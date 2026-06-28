from __future__ import annotations

import argparse

from .config import AppConfig
from .responder import AutoResponder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gmail automated reply framework")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without creating drafts")
    parser.add_argument("--send", action="store_true", help="Send replies instead of creating drafts")
    parser.add_argument("--dashboard", action="store_true", help="Start the local dashboard")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = AppConfig.from_env()
    if args.dashboard:
        from .dashboard import run_dashboard

        run_dashboard(config)
        return 0

    responder = AutoResponder(config)
    send_now = args.send and not args.dry_run and not config.draft_only
    result = responder.run(dry_run=args.dry_run, send_now=send_now)

    print(
        f"Scanned={result.scanned} Replied={result.replied} "
        f"Skipped={result.skipped} Failed={result.failed} "
        f"Mode={'dry-run' if args.dry_run else 'send' if send_now else 'draft'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
