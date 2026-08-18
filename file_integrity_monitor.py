#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

BASELINE_FILENAME = ".fim_baseline.json"


def hash_file(filepath, chunk_size=65536):
   
  """Return SHA-256 hash of a file's contents."""
  
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (PermissionError, FileNotFoundError, OSError) as e:
        return f"ERROR:{e}"


def scan_directory(root_dir, exclude=None):
   
  """Walk directory tree and return {relative_path: hash} for all files."""
  
    exclude = exclude or {BASELINE_FILENAME}
    results = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip hidden/system dirs like .git to reduce noise
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fname in filenames:
            if fname in exclude:
                continue
            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, root_dir)
            results[rel_path] = {
                "hash": hash_file(full_path),
                "size": os.path.getsize(full_path) if os.path.exists(full_path) else 0,
                "mtime": os.path.getmtime(full_path) if os.path.exists(full_path) else 0,
            }
    return results


def load_baseline(root_dir):
    path = os.path.join(root_dir, BASELINE_FILENAME)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def save_baseline(root_dir, data):
    path = os.path.join(root_dir, BASELINE_FILENAME)
    payload = {
        "created": datetime.now(timezone.utc).isoformat(),
        "root": os.path.abspath(root_dir),
        "files": data,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


def compare(baseline_files, current_files):
   
  """Return dict of added / removed / modified files."""

    baseline_set = set(baseline_files.keys())
    current_set = set(current_files.keys())

    added = sorted(current_set - baseline_set)
    removed = sorted(baseline_set - current_set)
    modified = sorted(
        f for f in (baseline_set & current_set)
        if baseline_files[f]["hash"] != current_files[f]["hash"]
    )
    return {"added": added, "removed": removed, "modified": modified}


def print_report(diff, root_dir):
    total_changes = len(diff["added"]) + len(diff["removed"]) + len(diff["modified"])
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if total_changes == 0:
        print(f"[{ts}] OK — no changes detected in {root_dir}")
        return False

    print(f"[{ts}] ALERT — {total_changes} change(s) detected in {root_dir}")
    if diff["added"]:
        print(f"  + Added ({len(diff['added'])}):")
        for f in diff["added"]:
            print(f"      + {f}")
    if diff["removed"]:
        print(f"  - Removed ({len(diff['removed'])}):")
        for f in diff["removed"]:
            print(f"      - {f}")
    if diff["modified"]:
        print(f"  ~ Modified ({len(diff['modified'])}):")
        for f in diff["modified"]:
            print(f"      ~ {f}")
    return True


def cmd_baseline(args):
    if not os.path.isdir(args.directory):
        sys.exit(f"Error: {args.directory} is not a directory")
    files = scan_directory(args.directory)
    path = save_baseline(args.directory, files)
    print(f"Baseline created: {path}")
    print(f"Tracked {len(files)} file(s).")


def cmd_scan(args):
    baseline = load_baseline(args.directory)
    if baseline is None:
        sys.exit(
            f"No baseline found in {args.directory}. "
            f"Run 'baseline' first."
        )
    current = scan_directory(args.directory)
    diff = compare(baseline["files"], current)
    changed = print_report(diff, args.directory)
    if args.update_on_scan:
        save_baseline(args.directory, current)
    sys.exit(1 if changed else 0)


def cmd_watch(args):
    print(f"Watching {args.directory} every {args.interval}s. Ctrl+C to stop.")
    baseline = load_baseline(args.directory)
    if baseline is None:
        print("No baseline found — creating one now.")
        files = scan_directory(args.directory)
        save_baseline(args.directory, files)
        baseline = {"files": files}

    try:
        while True:
            time.sleep(args.interval)
            current = scan_directory(args.directory)
            diff = compare(baseline["files"], current)
            changed = print_report(diff, args.directory)
            if changed:
                baseline = {"files": current}
                if args.update_on_scan:
                    save_baseline(args.directory, current)
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="File Integrity Monitor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_base = sub.add_parser("baseline", help="Create/update the baseline")
    p_base.add_argument("directory")
    p_base.set_defaults(func=cmd_baseline)

    p_scan = sub.add_parser("scan", help="Scan once and report changes")
    p_scan.add_argument("directory")
    p_scan.add_argument("--update-on-scan", action="store_true",
                         help="Update baseline to current state after reporting")
    p_scan.set_defaults(func=cmd_scan)

    p_watch = sub.add_parser("watch", help="Continuously monitor at an interval")
    p_watch.add_argument("directory")
    p_watch.add_argument("--interval", type=int, default=30, help="Seconds between scans")
    p_watch.add_argument("--update-on-scan", action="store_true",
                          help="Auto-update baseline after each detected change")
    p_watch.set_defaults(func=cmd_watch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
