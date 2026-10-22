import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .core import atomic_json, merge, public_jobs
from .render import render
from .sources import discover, verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", action="store_true", help="Search six weeks instead of seven days")
    parser.add_argument("--import-dir", type=Path, help="Import saved JobSpy query-*.json files")
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--skip-verification", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "config.json").read_text())
    now = datetime.now(ZoneInfo(config["timezone"])).isoformat(timespec="seconds")
    path = ROOT / "data/jobs.json"
    existing = public_jobs(json.loads(path.read_text())) if path.exists() else []
    health_path = ROOT / "data/health.json"
    if args.render_only:
        jobs = existing
        health = json.loads(health_path.read_text()) if health_path.exists() else []
    else:
        if args.import_dir:
            files = sorted(args.import_dir.glob("query-*.json"))
            if not files:
                raise ValueError("No query-*.json input files; no output written")
            rows = [r for f in files for r in json.loads(f.read_text())]
            health = [{"source": "Initial saved JobSpy test", "status": "ok", "count": len(rows)}]
        else:
            rows, health = discover(config, config["lookback_days"] if args.backfill else config["daily_lookback_days"])
        # No usable data: preserve jobs entirely; write failure report for Actions.
        if not rows:
            atomic_json(path, existing)
            atomic_json(health_path, health)
            render(ROOT, existing, health, now)
            print("No rows received. Existing job data preserved; inspect source health.")
            return 1
        jobs = merge(existing, rows, config, now)
        if not args.skip_verification:
            print("Posting checks:", verify(jobs, config, now), flush=True)
    jobs = public_jobs(jobs)
    atomic_json(path, jobs)
    atomic_json(health_path, health)
    render(ROOT, jobs, health, now)
    print(json.dumps({"records": len(jobs), "verified": sum(j['status'] == 'Posting verified' for j in jobs), "sources": health}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
