from __future__ import annotations

import argparse
import json
from pathlib import Path

from .journal import JournalError, verify_journal


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
    args = parser.parse_args(argv)

    try:
        verification = verify_journal(args.path)
    except (JournalError, OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 1

    print(
        json.dumps(
            {"ok": True, "verification": verification.to_dict()},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
