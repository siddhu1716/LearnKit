import argparse
import json
import sys
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
    maintain_parser = subparsers.add_parser(
        "maintain", help="Run memory maintenance loops (decay, stale marking, quarantine promotion)"
    )
    maintain_parser.add_argument(
        "--db-path", type=str, default="~/.learnkit/memory.db", help="Path to SQLite database"
    )
    maintain_parser.add_argument(
        "--weeks", type=int, default=1, help="Number of weeks for confidence decay threshold"
    )
    maintain_parser.add_argument(
        "--decay-rate", type=float, default=0.02, help="Rate of confidence decay"
    )
    maintain_parser.add_argument(
        "--quarantine-hours",
        type=float,
        default=24.0,
        help="Minimum age in hours to promote quarantined records",
    )
    maintain_parser.add_argument(
        "--consolidate",
        action="store_true",
        help="Merge overlapping skills into umbrellas (archives near-duplicates)",
    )

    # Skills command — export the learned procedural skill library.
    skills_parser = subparsers.add_parser(
        "skills", help="Export the learned procedural skill library"
    )
    skills_sub = skills_parser.add_subparsers(dest="skills_command")
    export_parser = skills_sub.add_parser("export", help="Export skills to disk")
    export_parser.add_argument(
        "--db-path", type=str, default="~/.learnkit/memory.db", help="Path to SQLite database"
    )
    export_parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="Output directory (learnkit/deepagents) or JSON file (golden-tests)",
    )
    export_parser.add_argument(
        "--format",
        choices=["learnkit", "deepagents", "golden-tests"],
        default="learnkit",
        help="Export format",
    )
    export_parser.add_argument(
        "--scope", type=str, default="team", help="Memory scope to export (user/team/public)"
    )

    mcp_parser = subparsers.add_parser(
        "mcp", help="Run the LearnKit coding-agent MCP server over stdio"
    )
    mcp_parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to SQLite database (defaults to LEARNKIT_DB_PATH or ~/.learnkit/memory.db)",
    )

    plugin_parser = subparsers.add_parser("plugin", help="Coding-agent plugin utilities")
    plugin_sub = plugin_parser.add_subparsers(dest="plugin_command")
    hook_parser = plugin_sub.add_parser("hook", help="Process one coding-agent lifecycle hook")
    hook_parser.add_argument("event", type=str, help="Host lifecycle event name")
    hook_parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host identifier used for hook output and dashboard attribution",
    )
    hook_parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to SQLite database (defaults to LEARNKIT_DB_PATH or ~/.learnkit/memory.db)",
    )
    hook_parser.add_argument("--state-dir", type=str, default=None, help="Hook journal directory")
    doctor_parser = plugin_sub.add_parser(
        "doctor", help="Validate coding-agent plugin prerequisites"
    )
    doctor_parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to SQLite database (defaults to LEARNKIT_DB_PATH or ~/.learnkit/memory.db)",
    )
    doctor_parser.add_argument("--state-dir", type=str, default=None, help="Hook journal directory")

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
    elif args.command == "skills":
        if args.skills_command != "export":
            parser.parse_args(["skills", "--help"])
            sys.exit(1)
        try:
            lk = LearnKit(memory_backend="sqlite", db_path=args.db_path, scope=args.scope)
            if args.format == "golden-tests":
                from learnkit.drift import export_golden_suite

                n = export_golden_suite(lk, args.out)
                print(f"Wrote {n} golden tool-sequence(s) to {args.out}")
            else:
                n = lk.export_skill_library(args.out, fmt=args.format)
                print(f"Exported {n} skill(s) as '{args.format}' to {args.out}")
            lk.shutdown()
        except Exception as e:
            print(f"ERROR: Skill export failed: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "mcp":
        from learnkit.mcp_server import run_server

        run_server(db_path=args.db_path)
    elif args.command == "plugin":
        if args.plugin_command == "hook":
            from learnkit.plugin_runtime import format_hook_output, handle_hook

            try:
                payload = json.load(sys.stdin)
            except json.JSONDecodeError:
                payload = {}
            output = handle_hook(
                args.event,
                payload if isinstance(payload, dict) else {},
                db_path=args.db_path,
                state_dir=args.state_dir,
                host=args.host,
            )
            formatted = format_hook_output(args.host, args.event, output)
            if formatted:
                sys.stdout.write(formatted)
        elif args.plugin_command == "doctor":
            from learnkit.plugin_runtime import doctor

            result = doctor(db_path=args.db_path, state_dir=args.state_dir)
            print(json.dumps(result, indent=2))
            if not result["ok"]:
                sys.exit(1)
        else:
            plugin_parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
