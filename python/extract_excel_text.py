# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pandas>=2.0.0",
#     "openpyxl>=3.1.0",
#     "xlrd>=2.0.1",
# ]
# ///

import argparse
import os
import sys
import pandas as pd


def extract_all_text(source_dir, output_path):
    if not os.path.isdir(source_dir):
        print(f"Error: The folder '{source_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    supported_extensions = (".xlsx", ".xls", ".csv")
    files_processed = 0

    with open(output_path, "w", encoding="utf-8") as out_file:
        for root, _, files in os.walk(source_dir):
            for file in files:
                # Skip temporary Excel lock files
                if file.startswith("~$") or not file.lower().endswith(
                    supported_extensions
                ):
                    continue

                file_path = os.path.join(root, file)
                out_file.write(f"\n{'=' * 80}\n")
                out_file.write(f"FILE: {file_path}\n")
                out_file.write(f"{'=' * 80}\n")

                try:
                    if file.lower().endswith(".csv"):
                        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
                        write_dataframe(out_file, "CSV_Data", df)
                    else:
                        excel_sheets = pd.read_excel(
                            file_path, sheet_name=None, dtype=str
                        )
                        for sheet_name, df in excel_sheets.items():
                            write_dataframe(out_file, sheet_name, df)

                    files_processed += 1
                    if files_processed % 100 == 0:
                        print(f"Processed {files_processed} files...")

                except Exception as e:
                    out_file.write(f"[ERROR reading file: {e}]\n")

    print(f"\nDone! Extracted text from {files_processed} files into '{output_path}'.")


def write_dataframe(out_file, sheet_name, df):
    out_file.write(f"\n--- Sheet: {sheet_name} ---\n")
    df = df.fillna("")
    for row_idx, row in df.iterrows():
        row_values = [str(val).strip() for val in row.values if str(val).strip() != ""]
        if row_values:
            out_file.write(f"Row {row_idx + 2}: {' | '.join(row_values)}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Crawl a folder and extract text from all Excel and CSV files."
    )
    parser.add_argument(
        "folder",
        help="Path to the folder containing Excel/CSV files",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="all_excel_contents.txt",
        help="Output text file path (default: all_excel_contents.txt)",
    )

    args = parser.parse_args()
    extract_all_text(args.folder, args.output)


if __name__ == "__main__":
    main()
