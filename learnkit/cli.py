import argparse
import sys
from pathlib import Path
from learnkit import __version__
from learnkit.core import LearnKit

def main():
    parser = argparse.ArgumentParser(description="LearnKit Command Line Interface")
    parser.add_argument(
        "--version",
        action="version",
        version=f"learnkit-ai {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Maintain command
    maintain_parser = subparsers.add_parser("maintain", help="Run memory maintenance loops (decay, stale marking, quarantine promotion)")
    maintain_parser.add_argument("--db-path", type=str, default="~/.learnkit/memory.db", help="Path to SQLite database")
    maintain_parser.add_argument("--weeks", type=int, default=1, help="Number of weeks for confidence decay threshold")
    maintain_parser.add_argument("--decay-rate", type=float, default=0.02, help="Rate of confidence decay")
    maintain_parser.add_argument("--quarantine-hours", type=float, default=24.0, help="Minimum age in hours to promote quarantined records")
    maintain_parser.add_argument("--consolidate", action="store_true", help="Merge overlapping skills into umbrellas (archives near-duplicates)")

    args = parser.parse_args()

    if args.command == "maintain":
        print(f"Running maintenance on database: {args.db_path}...")
        try:
            lk = LearnKit(memory_backend="sqlite", db_path=args.db_path)
            stats = lk.maintain_memory(
                weeks=args.weeks,
                decay_rate=args.decay_rate,
                quarantine_hours=args.quarantine_hours,
                consolidate=args.consolidate,
            )
            print("Maintenance completed successfully:")
            print(f"  Decayed records:    {stats.get('decayed', 0)}")
            print(f"  Expired/stale marked: {stats.get('stale', 0)}")
            print(f"  Quarantine promoted: {stats.get('promoted', 0)}")
            if args.consolidate:
                print(f"  Skill clusters merged: {stats.get('consolidated_clusters', 0)}")
                print(f"  Skills archived:    {stats.get('consolidated_archived', 0)}")
            lk.shutdown()
        except Exception as e:
            print(f"ERROR: Maintenance failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
