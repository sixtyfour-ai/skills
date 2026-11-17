#!/usr/bin/env python3
"""
Poll a Sixtyfour Job until it finishes and optionally download its results.

Every /v1 start (contacts, intelligence, search, age verification, workflow
runs, exports) returns a job_id. This script follows it at GET /v1/jobs/{job_id}.

Usage:
  python3 poll_job.py <job_id> [--timeout 900] [--output /tmp/results.csv]

With --output:
  - a Workflow Job downloads the files listed in its result;
  - any other Job is exported to CSV (POST /v1/exports) and downloaded.

Environment:
  SIXTYFOUR_API_KEY       Required. Get one at https://app.sixtyfour.ai/keys
  SIXTYFOUR_API_ENDPOINT  Optional. Defaults to https://api.sixtyfour.ai
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

FINAL_STATUSES = ("succeeded", "failed", "canceled")


def _log(data):
    print(json.dumps(data), flush=True)


def _request(method, path, api_key, base_url, body=None):
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        _log({"error": f"HTTP {e.code}", "detail": e.read().decode() if e.fp else ""})
        sys.exit(1)


def _download(url, path, api_key):
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    with urllib.request.urlopen(req) as resp, open(path, "wb") as f:
        f.write(resp.read())


def poll(job_id, api_key, base_url, deadline):
    """Return the finished Job, or None when the deadline passes first."""
    delay = 5
    start = time.time()
    while time.time() < deadline:
        job = _request("GET", f"/v1/jobs/{job_id}", api_key, base_url)
        _log({
            "job_id": job_id,
            "operation": job.get("operation"),
            "status": job.get("status"),
            "counts": job.get("counts"),
            "elapsed_s": round(time.time() - start),
        })
        if job.get("status") in FINAL_STATUSES:
            return job
        delay = job.get("next_poll_after") or delay
        time.sleep(delay)
    return None


def save_results(job, output, api_key, base_url, deadline):
    result = job.get("result")
    if isinstance(result, list):
        # A Workflow Job lists one file per output block.
        for i, item in enumerate(result):
            path = output if i == 0 else f"{output}.part{i}"
            _download(item["download_url"], path, api_key)
            _log({"result": "downloaded", "path": path, "rows": item.get("row_count"), "filename": item.get("filename")})
        return 0

    export = _request("POST", "/v1/exports", api_key, base_url, {"from": {"job_id": job["job_id"]}, "format": "csv"})
    export = poll(export["job_id"], api_key, base_url, deadline)
    if not export or export["status"] != "succeeded":
        _log({"result": "export_failed", "detail": export})
        return 1
    file = _request("GET", f"/v1/files/{export['result']['output_file_id']}", api_key, base_url)
    _download(file["download_url"], output, api_key)
    _log({"result": "downloaded", "path": output, "rows": file.get("row_count")})
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Poll a Sixtyfour Job and optionally download its results.",
        epilog="Set SIXTYFOUR_API_KEY before running. Get a key at https://app.sixtyfour.ai/keys",
    )
    parser.add_argument("job_id", help="The job_id a /v1 start returned")
    parser.add_argument("--timeout", type=int, default=86400, help="Max seconds to wait (default: 86400)")
    parser.add_argument("--output", "-o", help="Download results to this file path")
    args = parser.parse_args()

    api_key = os.environ.get("SIXTYFOUR_API_KEY")
    if not api_key:
        _log({"error": "SIXTYFOUR_API_KEY environment variable not set", "fix": "Get an API key at https://app.sixtyfour.ai/keys and run: export SIXTYFOUR_API_KEY=your_key"})
        sys.exit(1)
    base_url = os.environ.get("SIXTYFOUR_API_ENDPOINT", "https://api.sixtyfour.ai")
    deadline = time.time() + args.timeout

    job = poll(args.job_id, api_key, base_url, deadline)
    if job is None:
        _log({"result": "timeout", "timeout_s": args.timeout})
        sys.exit(1)
    if job["status"] != "succeeded":
        _log({"result": job["status"], "detail": job})
        sys.exit(1)
    if args.output:
        sys.exit(save_results(job, args.output, api_key, base_url, deadline))
    _log({"result": "succeeded", "job": job})


if __name__ == "__main__":
    main()
