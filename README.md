# File Integrity Monitor (FIM)

A Python CLI tool that detects unauthorized changes to files by comparing SHA-256 hashes against a saved baseline — inspired by tools like Tripwire and OSSEC.

## Features

- Recursive directory scanning with SHA-256 hashing
- JSON-based baseline storage (hash, size, mtime per file)
- Detects **added**, **removed**, and **modified** files
- Continuous `watch` mode with configurable polling interval
- Exit codes suitable for scripting, cron jobs, or CI pipelines

## Requirements

- Python 3.8+
- No external dependencies (standard library only)

## Usage

**Create a baseline:**
```bash
python file_integrity_monitor.py baseline /path/to/directory
```

**Scan once and report changes:**
```bash
python file_integrity_monitor.py scan /path/to/directory
```
Add `--update-on-scan` to refresh the baseline after reporting.

**Continuously monitor:**
```bash
python file_integrity_monitor.py watch /path/to/directory --interval 30
```

## How it works

1. `baseline` walks the target directory and records a SHA-256 hash, file size, and modification time for every file, saving the result as `.fim_baseline.json` inside the directory.
2. `scan` re-hashes the current state and diffs it against the baseline, printing any additions, deletions, or modifications.
3. `watch` repeats the scan on a timer, automatically re-baselining after each detected change.

## Example output

```
[2026-08-18 04:55:55 UTC] ALERT — 2 change(s) detected in testdir
  + Added (1):
      + b.txt
  ~ Modified (1):
      ~ a.txt
```

## Possible extensions

- Email or Slack webhook alerts
- Whitelist/exclude patterns for expected changes (logs, caches)
- Git-committed baseline for tamper-evident history
- Recursive exclude flags for directories like `node_modules`

## License

MIT
