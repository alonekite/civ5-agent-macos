from __future__ import annotations

import argparse
import json
from pathlib import Path

from .journal import (
    JournalError,
    export_redacted_journal,
    replay_journal,
    verify_journal,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a private Civilization V match journal"
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    verify_parser = subparsers.add_parser(
        "verify",
        help="validate the full journal and print a payload-free summary",
    )
    verify_parser.add_argument("path", type=Path)
    replay_parser = subparsers.add_parser(
        "replay",
        help="validate and emit ordered factual events (contains private payloads)",
    )
    replay_parser.add_argument("path", type=Path)
    replay_parser.add_argument(
        "--include-private-payloads",
        action="store_true",
        help="acknowledge that snapshot and command payloads may be private",
    )
    export_parser = subparsers.add_parser(
        "export",
        help="write a new mode-0600 structural export with private fields removed",
    )
    export_parser.add_argument("source", type=Path)
    export_parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.operation == "verify":
            result = {
                "ok": True,
                "verification": verify_journal(args.path).to_dict(),
            }
        elif args.operation == "replay":
            if not args.include_private_payloads:
                parser.error("replay requires --include-private-payloads")
            result = {
                "ok": True,
                "events": [event.to_dict() for event in replay_journal(args.path)],
            }
        else:
            result = {
                "ok": True,
                "export": export_redacted_journal(
                    args.source,
                    args.destination,
                ).to_dict(),
            }
    except (JournalError, OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
