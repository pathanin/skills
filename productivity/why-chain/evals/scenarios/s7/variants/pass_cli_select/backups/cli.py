import argparse

from .pruner import prune, select_for_deletion
import os


def main(argv=None):
    parser = argparse.ArgumentParser(prog="backups")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prune", help="delete old backups, keeping the newest N")
    p.add_argument("directory")
    p.add_argument("--keep", type=int, default=7)
    p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "prune" and args.dry_run:
        for name in select_for_deletion(os.listdir(args.directory), args.keep):
            print(f"[dry-run] {name}")
        return 0
    if args.command == "prune":
        deleted = prune(args.directory, args.keep)
        for name in deleted:
            print(f"deleted {name}")
        print(f"{len(deleted)} backup(s) removed")
    return 0
