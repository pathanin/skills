import argparse

from .pruner import prune


def main(argv=None):
    parser = argparse.ArgumentParser(prog="backups")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prune", help="delete old backups, keeping the newest N")
    p.add_argument("directory")
    p.add_argument("--keep", type=int, default=7)
    args = parser.parse_args(argv)

    if args.command == "prune":
        deleted = prune(args.directory, args.keep)
        for name in deleted:
            print(f"deleted {name}")
        print(f"{len(deleted)} backup(s) removed")
    return 0
