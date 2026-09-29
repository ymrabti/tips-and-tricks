import os
import sys
import argparse
import win32com.client

def format_size(size_in_bytes):
    """Dynamically parses and formats bytes into KB, MB, or GB."""
    if size_in_bytes == 0:
        return "0 KB"
    for unit in ['Bytes', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def convert_ms_office_to_pdf_recursive(root_folder_path, dry_run=False):
    if not os.path.isdir(root_folder_path):
        print(f"Error: '{root_folder_path}' is not a valid directory.")
        sys.exit(1)

    # Reference definitions for MS Office export formats
    WD_FORMAT_PDF = 17
    XL_FORMAT_PDF = 0
    PPT_FORMAT_PDF = 32

    # Initialize variables for the applications
    word_app = None
    excel_app = None
    ppt_app = None

    scan_count = 0
    
    # Trackers for counts
    converted_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Trackers for file sizes (in bytes)
    converted_size = 0
    skipped_size = 0
    failed_size = 0

    if dry_run:
        print(f"\n[DRY RUN] Scanning root folder and subfolders: {root_folder_path}")
        print("No files will be modified.\n" + "-"*50)
    else:
        print(f"\nProcessing root folder and subfolders: {root_folder_path}\n" + "-"*50)

    try:
        for dirpath, _, filenames in os.walk(root_folder_path):
            for file in filenames:
                file_lower = file.lower()
                
                # Skip temporary hidden Office files (e.g., ~$document.docx)
                if file.startswith("~$"):
                    continue
                    
                input_file_path = os.path.abspath(os.path.join(dirpath, file))
                output_pdf_path = os.path.splitext(input_file_path)[0] + ".pdf"
                
                # Check extensions
                is_word = file_lower.endswith(('.doc', '.docx'))
                is_excel = file_lower.endswith(('.xls', '.xlsx'))
                is_ppt = file_lower.endswith(('.ppt', '.pptx'))

                if is_word or is_excel or is_ppt:
                    scan_count += 1
                    relative_display_path = os.path.join(os.path.basename(dirpath), file)
                    
                    try:
                        file_size = os.path.getsize(input_file_path)
                    except Exception:
                        file_size = 0

                    # Skip if already converted
                    if os.path.exists(output_pdf_path):
                        skipped_count += 1
                        skipped_size += file_size
                        if dry_run:
                            print(f"[Skipped - PDF Exists] {relative_display_path} ({format_size(file_size)})")
                        continue

                    if dry_run:
                        file_type = "Word" if is_word else "Excel" if is_excel else "PowerPoint"
                        print(f"[Would Convert] {file_type} file: {relative_display_path} ({format_size(file_size)})")
                        continue

                    # Individual try-except block ensures single-file errors don't crash the script
                    try:
                        # 1. Word Files
                        if is_word:
                            if not word_app:
                                word_app = win32com.client.Dispatch("Word.Application")
                                word_app.Visible = False
                            
                            print(f"Converting Word document: {relative_display_path}")
                            doc = word_app.Documents.Open(input_file_path)
                            doc.SaveAs(output_pdf_path, FileFormat=WD_FORMAT_PDF)
                            doc.Close()
                            converted_count += 1
                            converted_size += file_size

                        # 2. Excel Files
                        elif is_excel:
                            if not excel_app:
                                excel_app = win32com.client.Dispatch("Excel.Application")
                                excel_app.Visible = False
                            
                            print(f"Converting Excel sheet: {relative_display_path}")
                            wb = excel_app.Workbooks.Open(input_file_path)
                            wb.ExportAsFixedFormat(XL_FORMAT_PDF, output_pdf_path)
                            wb.Close(False)
                            converted_count += 1
                            converted_size += file_size

                        # 3. PowerPoint Files
                        elif is_ppt:
                            if not ppt_app:
                                ppt_app = win32com.client.Dispatch("PowerPoint.Application")
                            
                            print(f"Converting PowerPoint deck: {relative_display_path}")
                            presentation = ppt_app.Presentations.Open(input_file_path, WithWindow=False)
                            presentation.SaveAs(output_pdf_path, FileFormat=PPT_FORMAT_PDF)
                            presentation.Close()
                            converted_count += 1
                            converted_size += file_size
                            
                    except Exception as file_error:
                        print(f"ERROR converting {relative_display_path}: {file_error}")
                        failed_count += 1
                        failed_size += file_size
                        continue

    except Exception as general_error:
        print(f"A critical error occurred during loop iteration: {general_error}")

    finally:
        # Safely shut down all background Microsoft applications
        if word_app:
            try: word_app.Quit() 
            except: pass
        if excel_app:
            try: excel_app.Quit() 
            except: pass
        if ppt_app:
            try: ppt_app.Quit() 
            except: pass

    # Print final execution metrics with adaptive size formats
    if dry_run:
        print(f"\n[DRY RUN COMPLETE]")
        print(f" - Total identified: {scan_count}")
        print(f" - Already converted (will skip): {skipped_count} ({format_size(skipped_size)})")
        print(f" - Pending conversion: {scan_count - skipped_count}")
    else:
        print(f"\nProcessing Complete!")
        print(f" - Successfully converted: {converted_count} file(s) [{format_size(converted_size)}]")
        print(f" - Skipped (PDF already exists): {skipped_count} file(s) [{format_size(skipped_size)}]")
        print(f" - Failed due to file errors: {failed_count} file(s) [{format_size(failed_size)}]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Office files in a directory recursively to PDF using MS Office.")
    parser.add_argument("folder", type=str, help="The path to the target root folder.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and list files without converting them.")
    
    args = parser.parse_args()
    
    target_folder = args.folder.strip()
    if target_folder.startswith(('"', "'")) and target_folder.endswith(('"', "'")):
        target_folder = target_folder[1:-1]
        
    convert_ms_office_to_pdf_recursive(target_folder, dry_run=args.dry_run)
