import argparse

from .pruner import prune


def main(argv=None):
    parser = argparse.ArgumentParser(prog="backups")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prune", help="delete old backups, keeping the newest N")
    p.add_argument("directory")
    p.add_argument("--keep", type=int, default=7)
    p.add_argument("--dry-run", action="store_true",
                   help="list the backups that would be deleted without deleting them")
    args = parser.parse_args(argv)

    if args.command == "prune":
        deleted = prune(args.directory, args.keep, dry_run=args.dry_run)
        verb = "would delete" if args.dry_run else "deleted"
        for name in deleted:
            print(f"{verb} {name}")
        if args.dry_run:
            print(f"{len(deleted)} backup(s) would be removed")
        else:
            print(f"{len(deleted)} backup(s) removed")
    return 0
