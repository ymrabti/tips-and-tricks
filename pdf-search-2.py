import fitz  # PyMuPDF
import os
import argparse
from tqdm import tqdm
import pandas as pd

def search_in_pdfs(folder_path, search_term):
    pdf_files = []
    matches = []

    # Recursively collect all PDF files
    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, filename))

    match_count = 0

    # Progress bar using tqdm
    for filepath in tqdm(pdf_files, desc="Processing PDFs", unit="file"):
        try:
            doc = fitz.open(filepath)
            for page_num, page in enumerate(doc):
                try:
                    text = page.get_text()
                    if search_term.lower() in text.lower():
                        match_count += 1
                        print(f"\n✅ Match #{match_count}: {filepath}, Page {page_num + 1}")
                        matches.append({
                            "file": filepath,
                            "page": page_num + 1
                        })
                except Exception as page_error:
                    print(f"\n⚠️ Could not extract text from {filepath}, page {page_num + 1}: {page_error}")
            doc.close()
        except Exception as doc_error:
            print(f"\n❌ Failed to open {filepath}: {doc_error}")

    # Save matches to CSV
    if matches:
        df = pd.DataFrame(matches)
        output_file = "pdf_matches.csv"
        df.to_csv(output_file, index=False)
        print(f"\n📄 Match summary saved to: {output_file}")
    else:
        print("\n❌ No matches found.")

    # Show final summary
    print("\n🎯 Search Complete")
    print(f"Total PDFs scanned: {len(pdf_files)}")
    print(f"Total matches found: {match_count}")

def main():
    parser = argparse.ArgumentParser(description="Recursively search for text in PDF files within a folder.")
    parser.add_argument("folder_path", help="Path to the folder containing PDFs")
    parser.add_argument("search_term", help="Text to search for in the PDFs")
    args = parser.parse_args()

    search_in_pdfs(args.folder_path, args.search_term)

if __name__ == "__main__":
    main()
