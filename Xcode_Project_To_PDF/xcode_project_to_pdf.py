#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xcode Project (or general directory) to PDF report.
Strips accents/■ to ASCII, uses Courier, and emits raw code.
Allows customization of ignored items, file type definitions, and content length limits.
Auto-installs ReportLab/Pillow if needed (can be disabled).
"""
import os
import sys
import subprocess
import argparse
import mimetypes
import datetime
import unicodedata

# Default Configurations (can be overridden by command-line arguments)
DEFAULT_IGNORE_DIRS  = {'.git','Pods','build','.swiftpm','DerivedData','.xcodeproj',
                        '.xcworkspace','Carthage','Scripts','xcuserdata'}
DEFAULT_IGNORE_FILES = {'.DS_Store','.gitignore','.gitattributes','.swiftlint.yml',
                        'Podfile.lock','Cartfile.resolved','.ruby-version','.tool-versions'}
DEFAULT_CODE_EXT     = {'.swift','.h','.m','.mm','.c','.cpp','.hpp','Podfile','Cartfile'}
DEFAULT_DATA_EXT     = {'.plist','.json','.xml','.yaml','.yml','.storyboard',
                        '.xib','.entitlements','.xcscheme','.md','.txt','.rtf'}
DEFAULT_MAX_CODE_LEN = -1  # -1 for unlimited
DEFAULT_MAX_DATA_LEN = 15000 # Truncate large data files by default

# ReportLab and Pillow will be imported after potential installation
reportlab_pagesizes = None
reportlab_platypus = None
reportlab_styles = None
reportlab_enums = None
reportlab_colors = None
MONO_FONT = 'Courier' # Default monospace font for ReportLab

# ─── SANITIZE (strip accents and ■) ───────────────────────────────────────────
def sanitize(text: str) -> str:
    """Converts text to basic ASCII, replacing ■ with _."""
    text = text.replace('■', '_') # Replace special box character
    nfkd_form = unicodedata.normalize('NFKD', text)
    return nfkd_form.encode('ASCII', 'ignore').decode('ASCII')

# ─── HELPERS ────────────────────────────────────────────────────────────────
def classify_file(path, code_extensions_set):
    """Classifies a file as 'code' or 'data' based on its extension."""
    _, ext = os.path.splitext(path)
    return 'code' if ext.lower() in code_extensions_set else 'data'

def is_text_file(path, code_extensions_set, data_extensions_set):
    """Determines if a file is likely a text file based on extension or MIME type."""
    _, ext = os.path.splitext(path)
    if ext.lower() in code_extensions_set or ext.lower() in data_extensions_set:
        return True
    
    # Fallback to MIME type guessing for other extensions
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type:
        return mime_type.startswith('text/') or \
               mime_type in ('application/xml', 'application/json', 'application/javascript')
    return False # Default to non-text if unsure

def get_directory_tree(root_path, ignore_dirs_set, ignore_files_set):
    """Generates a string representation of the directory tree."""
    lines = []
    sanitized_root_basename = sanitize(os.path.basename(os.path.abspath(root_path)))
    lines.append(f"{sanitized_root_basename}/")

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        # Filter ignored directories in-place to prevent os.walk from descending into them
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs_set and not d.startswith('.')]
        
        relative_dir_path = os.path.relpath(dirpath, root_path)
        level = 0 if relative_dir_path == '.' else relative_dir_path.count(os.sep) + 1
        
        indent = '  ' * level
        if relative_dir_path != '.': # Add directory entry if not the root itself
            lines.append(f"{indent[:-2]}{sanitize(os.path.basename(dirpath))}/") # Correct indent for dir

        for filename in sorted(filenames):
            if filename in ignore_files_set or filename.startswith('.'):
                continue
            lines.append(f"{indent}{sanitize(filename)}")
            
    return "\n".join(lines)

def get_file_content_and_status(path, max_code_len, max_data_len, code_ext_set, data_ext_set):
    """Reads file content, sanitizes it, and provides status info (full, partial, non-text, error)."""
    info = {'status': 'Unknown', 'extracted_chars': None, 'total_chars': None, 'error_message': None}
    filename = os.path.basename(path)

    try:
        if not is_text_file(path, code_ext_set, data_ext_set):
            info['status'] = 'Non-Text'
            return "[Non-text file; content not displayed]", info

        file_type = classify_file(path, code_ext_set)
        limit = -1
        if filename == 'project.pbxproj': # Always try to get full pbxproj
            limit = -1
        elif file_type == 'code':
            limit = max_code_len
        else: # data or other text files
            limit = max_data_len
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            # Replace tabs with 4 spaces for consistent formatting in PDF
            text_content = f.read().replace('\t', '    ') 
        
        sanitized_content = sanitize(text_content)
        total_chars = len(sanitized_content)
        info['total_chars'] = total_chars

        if limit != -1 and total_chars > limit:
            snippet = sanitized_content[:limit]
            info.update(status='Partial', extracted_chars=len(snippet))
            return snippet + f"\n\n[Content truncated at {info['extracted_chars']} characters]", info
        
        info.update(status='Full', extracted_chars=total_chars)
        return sanitized_content, info

    except Exception as e:
        info.update(status='Error', error_message=str(e))
        return f"[Error reading file {filename}: {e}]", info

def generate_summary_table(summary_data):
    """Generates a ReportLab Table for the file extraction summary."""
    global reportlab_platypus, reportlab_styles, reportlab_colors # Use globally imported modules

    header = ['File Path', 'Status', 'Details']
    table_data = [header]

    # Define paragraph styles for table cells
    path_style = reportlab_styles.ParagraphStyle('PathStyle', fontName=MONO_FONT, fontSize=8, leading=9, alignment=reportlab_enums.TA_LEFT)
    status_style_normal = reportlab_styles.ParagraphStyle('StatusStyleNormal', fontSize=8, leading=9, alignment=reportlab_enums.TA_CENTER)
    status_style_partial = reportlab_styles.ParagraphStyle('StatusStylePartial', fontSize=8, leading=9, alignment=reportlab_enums.TA_CENTER, textColor=reportlab_colors.red)
    status_style_error = reportlab_styles.ParagraphStyle('StatusStyleError', fontSize=8, leading=9, alignment=reportlab_enums.TA_CENTER, textColor=reportlab_colors.darkred)
    details_style = reportlab_styles.ParagraphStyle('DetailsStyle', fontSize=8, leading=9, alignment=reportlab_enums.TA_CENTER)

    table_style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), reportlab_colors.grey),    # Header background
        ('TEXTCOLOR', (0, 0), (-1, 0), reportlab_colors.whitesmoke), # Header text
        ('GRID', (0, 0), (-1, -1), 1, reportlab_colors.black),       # Grid for all cells
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),                     # Vertical alignment
    ]

    for i, item_info in enumerate(sorted(summary_data, key=lambda x: x['relative_path']), start=1):
        status = item_info['status']
        relative_path_sanitized = sanitize(item_info['relative_path'])
        
        path_paragraph = reportlab_platypus.Paragraph(relative_path_sanitized, path_style)
        details_paragraph_text = "N/A"

        if status == 'Full':
            status_paragraph = reportlab_platypus.Paragraph('Full', status_style_normal)
            details_paragraph_text = f"{item_info['total_chars']} chars"
        elif status == 'Partial':
            percentage = int((item_info['extracted_chars'] / item_info['total_chars']) * 100) if item_info['total_chars'] else 0
            status_paragraph = reportlab_platypus.Paragraph(f'Partial ({percentage}%)', status_style_partial)
            details_paragraph_text = f"{item_info['extracted_chars']} / {item_info['total_chars']} chars"
        elif status == 'Non-Text':
            status_paragraph = reportlab_platypus.Paragraph('Non-Text', status_style_normal)
        else: # Error
            status_paragraph = reportlab_platypus.Paragraph('Error', status_style_error)
            details_paragraph_text = item_info.get('error_message', '')[:40] # Truncate long error messages
            table_style_commands.append(('BACKGROUND', (0, i), (-1, i), reportlab_colors.lightpink)) # Highlight error rows

        details_paragraph = reportlab_platypus.Paragraph(details_paragraph_text, details_style)
        table_data.append([path_paragraph, status_paragraph, details_paragraph])
    
    # Define column widths (total width should be less than page width minus margins)
    # Letter page width is 612 points. Margins typically 72 points each side (1 inch).
    # Available width = 612 - 72 - 72 = 468 points.
    table = reportlab_platypus.Table(table_data, colWidths=[300, 70, 98])
    table.setStyle(reportlab_styles.TableStyle(table_style_commands))
    return table

def generate_pdf(root_dir, output_pdf_path, 
                 max_code_len_cfg, max_data_len_cfg,
                 ignore_dirs_set_cfg, ignore_files_set_cfg,
                 code_ext_set_cfg, data_ext_set_cfg):
    """Generates the full PDF report."""
    global reportlab_platypus, reportlab_styles, reportlab_colors, reportlab_pagesizes # Use globally imported modules

    abs_root_dir = os.path.abspath(root_dir)
    project_name_sanitized = sanitize(os.path.basename(abs_root_dir))
    generation_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    doc = reportlab_platypus.SimpleDocTemplate(output_pdf_path, pagesize=reportlab_pagesizes.letter)
    
    # Define styles
    styles = reportlab_styles.getSampleStyleSheet()
    heading1_style = styles['Heading1']
    heading2_style = styles['Heading2']
    meta_info_style = reportlab_styles.ParagraphStyle('MetaInfo', fontSize=9, textColor=reportlab_colors.darkgrey, spaceBefore=6)
    tree_style = reportlab_styles.ParagraphStyle('DirectoryTree', fontName=MONO_FONT, fontSize=9, leading=11)
    content_style = reportlab_styles.ParagraphStyle('FileContent', fontName=MONO_FONT, fontSize=8.5, leading=10)

    story = [
        reportlab_platypus.Paragraph(f"Project Report: {project_name_sanitized}", heading1_style),
        reportlab_platypus.Paragraph(f"Generated: {generation_timestamp}<br/>Source Directory: {abs_root_dir}", meta_info_style),
        reportlab_platypus.Spacer(1, 12), # 12 points of vertical space
        reportlab_platypus.Paragraph("Directory Tree Overview", heading2_style),
        reportlab_platypus.Preformatted(get_directory_tree(abs_root_dir, ignore_dirs_set_cfg, ignore_files_set_cfg), tree_style),
        reportlab_platypus.PageBreak(),
    ]

    # Collect summary data
    file_summary_data = []
    for dirpath, dirnames, filenames in os.walk(abs_root_dir, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs_set_cfg and not d.startswith('.')]
        for filename in sorted(filenames):
            if filename in ignore_files_set_cfg or filename.startswith('.'):
                continue
            full_path = os.path.join(dirpath, filename)
            _, status_info = get_file_content_and_status(full_path, max_code_len_cfg, max_data_len_cfg, code_ext_set_cfg, data_ext_set_cfg)
            status_info['relative_path'] = os.path.relpath(full_path, abs_root_dir)
            file_summary_data.append(status_info)

    story.extend([
        reportlab_platypus.Paragraph("File Extraction Summary", heading2_style),
        generate_summary_table(file_summary_data),
        reportlab_platypus.PageBreak(),
        reportlab_platypus.Paragraph("Detailed File Contents", heading2_style),
        reportlab_platypus.Spacer(1, 6),
    ])

    # Add file contents
    for dirpath, dirnames, filenames in os.walk(abs_root_dir, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs_set_cfg and not d.startswith('.')]
        for filename in sorted(filenames):
            if filename in ignore_files_set_cfg or filename.startswith('.'):
                continue
            
            full_path = os.path.join(dirpath, filename)
            relative_path_sanitized = sanitize(os.path.relpath(full_path, abs_root_dir))
            
            content_text, _ = get_file_content_and_status(full_path, max_code_len_cfg, max_data_len_cfg, code_ext_set_cfg, data_ext_set_cfg)
            
            story.extend([
                reportlab_platypus.Paragraph(f"File: {relative_path_sanitized}", heading2_style),
                reportlab_platypus.Preformatted(content_text, content_style),
                reportlab_platypus.Spacer(1, 12),
            ])

    doc.build(story)
    print(f"✅ PDF report generated successfully: {output_pdf_path}")

# ─── MAIN EXECUTION ───────────────────────────────────────────────────────────
def main():
    """Parses arguments, sets up configuration, and generates the PDF report."""
    global reportlab_pagesizes, reportlab_platypus, reportlab_styles, reportlab_enums, reportlab_colors # Make them assignable

    parser = argparse.ArgumentParser(
        description="Generate a PDF report from a project directory, typically an Xcode project.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('project_path', 
                        help="Root directory of the project to report on.")
    parser.add_argument('output_pdf', 
                        help="Path where the output PDF file will be saved.")
    
    # Configuration overrides
    parser.add_argument('--ignore-dirs', type=str, default=None,
                        help="Comma-separated list of directory names to ignore.\n"
                             "Example: '.git,build,DerivedData'\n"
                             f"(Default: {','.join(sorted(list(DEFAULT_IGNORE_DIRS)))})")
    parser.add_argument('--ignore-files', type=str, default=None,
                        help="Comma-separated list of exact file names to ignore.\n"
                             "Example: '.DS_Store,.gitignore'\n"
                             f"(Default: {','.join(sorted(list(DEFAULT_IGNORE_FILES)))})")
    parser.add_argument('--code-exts', type=str, default=None,
                        help="Comma-separated list of extensions for 'code' files (influences max length).\n"
                             "Example: '.swift,.py,.js'\n"
                             f"(Default: {','.join(sorted(list(DEFAULT_CODE_EXT)))})")
    parser.add_argument('--data-exts', type=str, default=None,
                        help="Comma-separated list of extensions for 'data' files (influences max length).\n"
                             "Example: '.json,.xml,.plist'\n"
                             f"(Default: {','.join(sorted(list(DEFAULT_DATA_EXT)))})")
    
    # Length limits
    parser.add_argument('--max-code-length', type=int, default=DEFAULT_MAX_CODE_LEN,
                        help=f"Maximum characters to extract from code files. Use -1 for unlimited. (Default: {DEFAULT_MAX_CODE_LEN})")
    parser.add_argument('--max-data-length', type=int, default=DEFAULT_MAX_DATA_LEN,
                        help=f"Maximum characters to extract from data files. Use -1 for unlimited. (Default: {DEFAULT_MAX_DATA_LEN})")
    
    # Installation flag
    parser.add_argument('--no-auto-install', action='store_true',
                        help="Disable automatic installation of missing 'reportlab' or 'pillow' libraries.")

    args = parser.parse_args()

    # --- Attempt to import or install ReportLab/Pillow ---
    try:
        from reportlab.lib import pagesizes as rl_pagesizes
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet as rl_getSampleStyleSheet
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.lib import colors as rl_colors
        # Pillow is an implicit dependency for images in ReportLab, ensure it's mentioned
        import PIL 
        
        # Assign to global scope for use in helper functions
        reportlab_pagesizes = rl_pagesizes
        reportlab_platypus = sys.modules['reportlab.platypus'] # Get module object
        reportlab_styles = sys.modules['reportlab.lib.styles']
        reportlab_enums = sys.modules['reportlab.lib.enums']
        reportlab_colors = rl_colors

    except ImportError:
        if not args.no_auto_install:
            print("Required libraries (reportlab or pillow) not found. Attempting to install...")
            pip_command = [sys.executable, "-m", "pip", "install", "--user", "reportlab", "pillow"]
            # Handle macOS specific flag if needed (though --user often suffices)
            if sys.platform == "darwin":
                 # For newer pip versions on system Python, this might be needed.
                 # However, --user should generally avoid needing this.
                 # Consider if this is still broadly necessary or if --user is enough.
                 # pip_command.append("--break-system-packages")
                 pass # --user should be sufficient in most cases to avoid system package issues.

            try:
                subprocess.check_call(pip_command)
                print("Libraries installed successfully. Please re-run the script.")
                sys.exit(0) # Exit for user to re-run, as imports need to be re-evaluated
            except subprocess.CalledProcessError as e:
                print(f"Error during installation: {e}")
                print("Please install them manually: 'pip install reportlab pillow'")
                sys.exit(1)
        else:
            print("Error: Required libraries 'reportlab' and 'pillow' are not installed.")
            print("Please install them manually (e.g., 'pip install reportlab pillow') or run without --no-auto-install.")
            sys.exit(1)
    
    # --- Process Configuration from Arguments ---
    ignore_dirs = set(args.ignore_dirs.split(',')) if args.ignore_dirs else DEFAULT_IGNORE_DIRS
    ignore_files = set(args.ignore_files.split(',')) if args.ignore_files else DEFAULT_IGNORE_FILES
    code_exts = set(e.strip().lower() for e in args.code_exts.split(',')) if args.code_exts else DEFAULT_CODE_EXT
    data_exts = set(e.strip().lower() for e in args.data_exts.split(',')) if args.data_exts else DEFAULT_DATA_EXT

    max_code = args.max_code_length
    max_data = args.max_data_length

    # --- Validate Paths ---
    if not os.path.isdir(args.project_path):
        print(f"Error: Project path '{args.project_path}' is not a valid directory.")
        sys.exit(1)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output_pdf)
    if output_dir and not os.path.exists(output_dir): # Check if output_dir is not empty (i.e. not current dir)
        try:
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        except OSError as e:
            print(f"Error: Could not create output directory '{output_dir}': {e}")
            sys.exit(1)

    # --- Generate PDF ---
    generate_pdf(
        args.project_path,
        args.output_pdf,
        max_code,
        max_data,
        ignore_dirs,
        ignore_files,
        code_exts,
        data_exts
    )

if __name__ == '__main__':
    main()
