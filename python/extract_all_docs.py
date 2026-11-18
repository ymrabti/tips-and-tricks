# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pandas>=2.0.0",
#     "openpyxl>=3.1.0",
#     "xlrd>=2.0.1",
#     "python-docx>=1.1.0",
#     "pypdf>=4.0.0",
# ]
# ///

import argparse
import os
import sys
import pandas as pd
from docx import Document
from pypdf import PdfReader


def process_folder(source_dir, output_dir):
    if not os.path.isdir(source_dir):
        print(f"Error: The folder '{source_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    supported_extensions = (".xlsx", ".xls", ".csv", ".docx", ".pdf")
    files_processed = 0

    for root, _, files in os.walk(source_dir):
        for file in files:
            # Skip temporary Office lock files and unsupported formats
            if file.startswith("~$") or not file.lower().endswith(supported_extensions):
                continue

            file_path = os.path.join(root, file)

            # Mirror the subfolder structure inside the output directory
            rel_dir = os.path.relpath(root, source_dir)
            target_dir = os.path.join(output_dir, rel_dir)
            os.makedirs(target_dir, exist_ok=True)

            # Append .txt to the original filename (e.g., report.pdf -> report.pdf.txt)
            # This prevents collisions between report.pdf and report.xlsx
            out_file_path = os.path.join(target_dir, f"{file}.txt")

            try:
                with open(out_file_path, "w", encoding="utf-8") as out_file:
                    out_file.write(f"SOURCE FILE: {file_path}\n")
                    out_file.write(f"{'=' * 80}\n\n")

                    ext = os.path.splitext(file)[1].lower()
                    if ext == ".csv":
                        extract_csv(file_path, out_file)
                    elif ext in (".xlsx", ".xls"):
                        extract_excel(file_path, out_file)
                    elif ext == ".docx":
                        extract_docx(file_path, out_file)
                    elif ext == ".pdf":
                        extract_pdf(file_path, out_file)

                files_processed += 1
                if files_processed % 100 == 0:
                    print(f"Processed {files_processed} files...")

            except Exception as e:
                print(f"[ERROR] Failed to process '{file_path}': {e}", file=sys.stderr)

    print(f"\nDone! Extracted {files_processed} files into '{output_dir}'.")


def extract_csv(file_path, out_file):
    df = pd.read_csv(file_path, header=None, dtype=str, keep_default_na=False)
    write_dataframe(out_file, "CSV_Data", df)


def extract_excel(file_path, out_file):
    excel_sheets = pd.read_excel(file_path, sheet_name=None, header=None, dtype=str)
    for sheet_name, df in excel_sheets.items():
        write_dataframe(out_file, sheet_name, df)


def write_dataframe(out_file, sheet_name, df):
    out_file.write(f"--- Sheet: {sheet_name} ---\n")
    df = df.fillna("")
    for row_idx, row in df.iterrows():
        row_values = [str(val).strip() for val in row.values if str(val).strip() != ""]
        if row_values:
            out_file.write(f"Row {row_idx + 1}: {' | '.join(row_values)}\n")
    out_file.write("\n")


def extract_docx(file_path, out_file):
    doc = Document(file_path)

    out_file.write("--- Document Paragraphs ---\n")
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            out_file.write(f"{text}\n")

    if doc.tables:
        out_file.write("\n--- Document Tables ---\n")
        for t_idx, table in enumerate(doc.tables, start=1):
            out_file.write(f"[Table {t_idx}]\n")
            for row in table.rows:
                row_values = [
                    cell.text.strip().replace("\n", " ") for cell in row.cells
                ]
                if any(row_values):
                    out_file.write(f"{' | '.join(row_values)}\n")
            out_file.write("\n")


def extract_pdf(file_path, out_file):
    reader = PdfReader(file_path)
    for page_num, page in enumerate(reader.pages, start=1):
        out_file.write(f"--- Page {page_num} ---\n")
        text = page.extract_text()
        if text and text.strip():
            out_file.write(f"{text.strip()}\n\n")
        else:
            out_file.write("[No extractable text on this page]\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from Excel, CSV, Word (.docx), and PDF files into individual .txt files."
    )
    parser.add_argument(
        "folder",
        help="Path to the source folder containing documents",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="extracted_texts",
        help="Destination folder for extracted .txt files (default: ./extracted_texts)",
    )

    args = parser.parse_args()
    process_folder(args.folder, args.output)

# uv run extract_all_docs.py "/path/to/folder" -o "/path/to/folder/index"

if __name__ == "__main__":
    main()
