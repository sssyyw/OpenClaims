#!/usr/bin/env python3
"""
Download DailyMed drug label XML zips for a list of brand names.

Usage:
    python3 download_dailymed.py <csv_file> [--start N] [--end N] [--out DIR]

The CSV is expected to have a header row and the brand name in the first column.
Rows are 1-indexed (row 1 = header). --start/--end are inclusive data-row numbers.

Example:
    python3 download_dailymed.py Top_Selling_Drugs_Adjusted.csv --start 2 --end 10
"""
import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request


def resolve_setid(name: str) -> str | None:
    """Look up a brand name via DailyMed's search API. Returns the first setid or None.

    Falls back to the first word of multi-word brand names.
    """
    attempts = [name]
    if " " in name:
        attempts.append(name.split()[0])
    for q in attempts:
        url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={urllib.parse.quote(q)}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = json.load(r)
        except Exception as e:
            print(f"  API error for {q!r}: {e}", file=sys.stderr)
            continue
        if data.get("data"):
            return data["data"][0]["setid"]
    return None


def download_zip(setid: str, out_path: str) -> int:
    url = f"https://dailymed.nlm.nih.gov/dailymed/downloadzipfile.cfm?setId={setid}"
    urllib.request.urlretrieve(url, out_path)
    return os.path.getsize(out_path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_file", help="CSV with brand names in column 1 (header row expected)")
    ap.add_argument("--start", type=int, default=2, help="First data row to process (1-indexed, default 2)")
    ap.add_argument("--end", type=int, default=None, help="Last data row to process (inclusive, default EOF)")
    ap.add_argument("--out", default=".", help="Output directory (default: current dir)")
    args = ap.parse_args()

    with open(args.csv_file) as f:
        rows = list(csv.reader(f))

    end = args.end if args.end is not None else len(rows)
    # Convert 1-indexed row numbers to 0-indexed slice
    targets = [r[0].strip() for r in rows[args.start - 1 : end] if r and r[0].strip()]
    print(f"Processing {len(targets)} drugs from {args.csv_file} rows {args.start}-{end}")

    os.makedirs(args.out, exist_ok=True)
    ok, missed, failed = [], [], []
    for name in targets:
        setid = resolve_setid(name)
        if not setid:
            print(f"MISS {name}: not found in DailyMed")
            missed.append(name)
            continue
        dest = os.path.join(args.out, f"{name}.zip")
        try:
            size = download_zip(setid, dest)
            print(f"OK   {name}: {size:,} bytes ({setid})")
            ok.append(name)
        except Exception as e:
            print(f"ERR  {name}: {e}")
            failed.append(name)

    print(f"\nSummary: {len(ok)} downloaded, {len(missed)} missing, {len(failed)} errored")
    if missed:
        print(f"Missing: {', '.join(missed)}")
    if failed:
        print(f"Errored: {', '.join(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
