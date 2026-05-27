#!/usr/bin/env python3
"""
Poll async Sixtyfour jobs and download results.

Usage:
  python3 poll_job.py search <task_id> [--timeout 600] [--output /tmp/results.csv]
  python3 poll_job.py workflow <run_id> [--timeout 1800] [--output /tmp/results.csv]
  python3 poll_job.py enrichment <job_id> [--timeout 900]

Environment:
  SIXTYFOUR_API_KEY       Required. Get one at https://app.sixtyfour.ai/keys
  SIXTYFOUR_API_ENDPOINT  Optional. Defaults to https://api.sixtyfour.ai
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error


def _request(method, path, api_key, base_url):
    url = f"{base_url}{path}"
    req = urllib.request.Request(
        url,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"_http_error": e.code, "_detail": body}


def _download(url, path):
    urllib.request.urlretrieve(url, path)


def _log(data):
    print(json.dumps(data), flush=True)


def poll_search(task_id, api_key, base_url, timeout, output, interval):
    start = time.time()
    while time.time() - start < timeout:
        resp = _request("GET", f"/search/status/{task_id}", api_key, base_url)
        if "_http_error" in resp:
            _log({"error": f"HTTP {resp['_http_error']}", "detail": resp["_detail"]})
            sys.exit(1)

        status = resp.get("status", "unknown")
        _log({
            "type": "search",
            "status": status,
            "elapsed_s": round(time.time() - start),
            "total_results": resp.get("total_results"),
            "message": resp.get("progress_message", ""),
        })

        if status == "completed":
            rhid = resp.get("resource_handle_id")
            if rhid and output:
                dl = _request("GET", f"/search/download?resource_handle_id={rhid}", api_key, base_url)
                signed_url = dl.get("url")
                if signed_url:
                    _download(signed_url, output)
                    _log({"result": "downloaded", "path": output, "total_results": resp.get("total_results")})
            else:
                _log({"result": "completed", "total_results": resp.get("total_results")})
            return 0

        if status == "failed":
            _log({"result": "failed", "detail": resp})
            return 1

        time.sleep(interval)

    _log({"result": "timeout", "timeout_s": timeout})
    return 1


def poll_workflow(run_id, api_key, base_url, timeout, output, interval):
    start = time.time()
    while time.time() - start < timeout:
        resp = _request("GET", f"/workflows/runs/{run_id}/live_status", api_key, base_url)
        if "_http_error" in resp:
            _log({"error": f"HTTP {resp['_http_error']}", "detail": resp["_detail"]})
            sys.exit(1)

        status = resp.get("overall_status", "unknown")
        _log({
            "type": "workflow",
            "status": status,
            "progress_pct": resp.get("overall_progress_percentage", 0),
            "elapsed_s": round(time.time() - start),
            "current_block": resp.get("current_block", ""),
            "completed_blocks": resp.get("completed_blocks"),
            "total_blocks": resp.get("total_blocks"),
        })

        if status == "completed":
            if output:
                links = _request("GET", f"/workflows/runs/{run_id}/results/download-links", api_key, base_url)
                if isinstance(links, list):
                    for i, link in enumerate(links):
                        path = output if i == 0 else f"{output}.part{i}"
                        _download(link["download_url"], path)
                        _log({"result": "downloaded", "path": path, "rows": link.get("row_count"), "filename": link.get("filename")})
                else:
                    _log({"result": "completed", "note": "no download links available"})
            else:
                _log({"result": "completed"})
            return 0

        if status in ("failed", "cancelled"):
            _log({"result": status, "detail": resp})
            return 1

        time.sleep(interval)

    _log({"result": "timeout", "timeout_s": timeout})
    return 1


def poll_enrichment(job_id, api_key, base_url, timeout, interval):
    start = time.time()
    while time.time() - start < timeout:
        resp = _request("GET", f"/job-status/{job_id}", api_key, base_url)
        if "_http_error" in resp:
            _log({"error": f"HTTP {resp['_http_error']}", "detail": resp["_detail"]})
            sys.exit(1)

        status = resp.get("status", "unknown")
        _log({
            "type": "enrichment",
            "status": status,
            "elapsed_s": round(time.time() - start),
        })

        if status == "completed":
            result = {k: v for k, v in resp.items() if k != "status"}
            _log({"result": "completed", "data": result})
            return 0

        if status == "failed":
            _log({"result": "failed", "detail": resp})
            return 1

        time.sleep(interval)

    _log({"result": "timeout", "timeout_s": timeout})
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="Poll async Sixtyfour jobs and download results.",
        epilog="Set SIXTYFOUR_API_KEY before running. Get a key at https://app.sixtyfour.ai/keys",
    )
    parser.add_argument("type", choices=["search", "workflow", "enrichment"], help="Job type to poll")
    parser.add_argument("job_id", help="Task ID (search), run ID (workflow), or job ID (enrichment)")
    parser.add_argument("--timeout", type=int, default=86400, help="Max seconds to wait (default: 86400 — effectively no limit)")
    parser.add_argument("--output", "-o", help="Download results to this file path (search and workflow only)")
    parser.add_argument("--interval", type=int, help="Poll interval in seconds (default: 12 for search, 8 for workflow, 10 for enrichment)")
    args = parser.parse_args()

    api_key = os.environ.get("SIXTYFOUR_API_KEY")
    if not api_key:
        _log({"error": "SIXTYFOUR_API_KEY environment variable not set", "fix": "Get an API key at https://app.sixtyfour.ai/keys and run: export SIXTYFOUR_API_KEY=your_key"})
        sys.exit(1)

    base_url = os.environ.get("SIXTYFOUR_API_ENDPOINT", "https://api.sixtyfour.ai")

    if args.type == "search":
        sys.exit(poll_search(args.job_id, api_key, base_url, args.timeout, args.output, args.interval or 12))
    elif args.type == "workflow":
        sys.exit(poll_workflow(args.job_id, api_key, base_url, args.timeout, args.output, args.interval or 8))
    elif args.type == "enrichment":
        sys.exit(poll_enrichment(args.job_id, api_key, base_url, args.timeout, args.interval or 10))


if __name__ == "__main__":
    main()
