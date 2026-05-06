"""Extract label statements from SPL zip files and write to CSV.

Usage:
    python scripts/extract_statements_csv.py /path/to/zip/folder/
    python scripts/extract_statements_csv.py /path/to/zip/folder/ --output statements.csv

Input: a folder of .zip files, one drug per zip. The zip filename is the drug name.
Each zip contains SPL XML files (DailyMed format).

Output: a CSV with columns: claim, product, manufacturer
"""

import argparse
import csv
import pathlib
import sys
import zipfile

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.labels.spl_parser import parse_spl_xml
from app.labels.statements import extract_statements


def process_zip(zip_path: pathlib.Path) -> list[dict]:
    """Extract statements from all XML files in a zip."""
    rows = []

    with zipfile.ZipFile(zip_path) as zf:
        xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
        if not xml_names:
            print(f"  WARNING: no XML files in {zip_path.name}")
            return rows

        for xml_name in xml_names:
            try:
                xml_content = zf.read(xml_name)
                label = parse_spl_xml(xml_content)
                statements = extract_statements(label)

                for s in statements:
                    rows.append({
                        "claim": s.text,
                        "product": label.drug_name,
                        "manufacturer": label.manufacturer,
                    })
            except Exception as e:
                print(f"  ERROR parsing {xml_name} in {zip_path.name}: {e}")

    return rows


def main():
    parser = argparse.ArgumentParser(description="Extract label statements to CSV")
    parser.add_argument("directory", type=pathlib.Path, help="Folder containing zip files")
    parser.add_argument("--output", "-o", type=pathlib.Path, default=None, help="Output CSV path")
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"Error: {args.directory} is not a directory")
        sys.exit(1)

    zip_files = sorted(args.directory.glob("*.zip"))
    if not zip_files:
        print(f"Error: no .zip files found in {args.directory}")
        sys.exit(1)

    output_path = args.output or pathlib.Path(f"statements.csv")

    print(f"Processing {len(zip_files)} zip files from {args.directory}")

    all_rows = []
    for i, zip_file in enumerate(zip_files, 1):
        print(f"  [{i}/{len(zip_files)}] {zip_file.stem}")
        rows = process_zip(zip_file)
        all_rows.extend(rows)
        print(f"    → {len(rows)} statements")

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["claim", "product", "manufacturer"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nDone: {len(all_rows)} statements written to {output_path}")


if __name__ == "__main__":
    main()
