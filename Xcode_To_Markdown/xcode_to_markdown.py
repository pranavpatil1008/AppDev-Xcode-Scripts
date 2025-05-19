#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xcode Project (or general directory) -> Markdown report.
Strips accents/■ to ASCII and emits Markdown formatted structure and code.
Allows customization of ignored items, file type definitions, and content length limits.
"""
import os
import sys
import argparse
import mimetypes
import datetime
import unicodedata

# ─── DEFAULT CONFIGURATIONS ───────────────────────────────────────────────────
DEFAULT_IGNORE_DIRS  = {'.git','Pods','build','.swiftpm','DerivedData','.xcodeproj',
                        '.xcworkspace','Carthage','Scripts','xcuserdata'}
DEFAULT_IGNORE_FILES = {'.DS_Store','.gitignore','.gitattributes','.swiftlint.yml',
                        'Podfile.lock','Cartfile.resolved','.ruby-version','.tool-versions',
                        'Package.resolved'}
DEFAULT_CODE_EXT     = {'.swift','.h','.m','.mm','.c','.cpp','.hpp','Podfile','Cartfile'}
DEFAULT_DATA_EXT     = {'.plist','.json','.xml','.yaml','.yml','.storyboard',
                        '.xib','.entitlements','.xcscheme','.md','.txt','.rtf'}

DEFAULT_MAX_CODE_LEN = 200000 
DEFAULT_MAX_DATA_LEN = 15000
DEFAULT_MAX_PBXPROJ_LEN = -1 

# ─── SANITIZE (strip accents and ■) ───────────────────────────────────────────
def sanitize(text: str) -> str:
    """Converts text to basic ASCII, replacing ■ with _."""
    text = text.replace('■', '_')
    nfd_form = unicodedata.normalize('NFD', text)
    return nfd_form.encode('ASCII', 'ignore').decode('ASCII')

# ─── HELPERS ────────────────────────────────────────────────────────────────
def classify_file(path, code_ext_set, data_ext_set):
    """Classifies a file as 'code', 'data', or 'other' based on its extension."""
    _, ext = os.path.splitext(path)
    if ext.lower() in code_ext_set:
        return 'code'
    if ext.lower() in data_ext_set:
        return 'data'
    return 'other'

def is_text_file(path, code_ext_set, data_ext_set):
    """Determines if a file is likely a text file."""
    file_type_by_ext = classify_file(path, code_ext_set, data_ext_set)
    if file_type_by_ext in ('code', 'data'):
        return True
    
    try:
        mt, _ = mimetypes.guess_type(path)
        if mt:
            if mt.startswith('text/'):
                return True
            if mt in ('application/xml', 'application/json', 'application/x-plist', 'application/yaml'):
                return True
    except Exception:
        pass
    return False

def get_directory_tree_md(root_path_param, current_ignore_dirs, current_ignore_files):
    """Generates a Markdown formatted string of the directory tree."""
    lines = []
    abs_root = os.path.abspath(root_path_param)
    project_name = sanitize(os.path.basename(abs_root))
    # print("Generating directory tree...") # Optional: for verbose output

    for dirpath, dirnames, filenames in os.walk(abs_root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in current_ignore_dirs and not d.startswith('.')]
        dirnames.sort()
        filenames.sort()

        relative_path_to_current_dir = os.path.relpath(dirpath, abs_root)
        
        level = 0
        if relative_path_to_current_dir == ".":
            lines.append(f"* **{project_name}/**")
        else:
            level = relative_path_to_current_dir.count(os.sep) + 1
            dir_indent = '  ' * (level - 1) if level > 0 else ''
            lines.append(f"{dir_indent}  * **{sanitize(os.path.basename(dirpath))}/**")
        
        file_indent = '  ' * level
        for fn in filenames:
            if fn in current_ignore_files or fn.startswith('.'):
                continue
            lines.append(f"{file_indent}  * {sanitize(fn)}")
            
    return "\n".join(lines)

def get_file_content_and_status(path, max_code, max_data, max_pbxproj, 
                                current_code_exts, current_data_exts):
    """Reads, sanitizes, and potentially truncates file content."""
    info = {'status':'Unknown','extracted_chars':None,'total_chars':None,'error_message':None}
    name = os.path.basename(path)
    try:
        if not is_text_file(path, current_code_exts, current_data_exts):
            info['status']='Non-Text'
            return "[Non-text file; content not displayed]", info
        
        limit = -1 
        file_class = classify_file(path, current_code_exts, current_data_exts)

        if name == 'project.pbxproj':
            limit = max_pbxproj
        elif file_class == 'code':
            limit = max_code
        elif file_class == 'data':
            limit = max_data
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            txt = f.read().replace('\t',' '*4)
        
        txt = sanitize(txt)
        total = len(txt)
        info['total_chars'] = total

        if limit != -1 and total > limit:
            snippet = txt[:limit]
            info.update(status='Partial', extracted_chars=len(snippet))
            return snippet + f"\n\n[Truncated at {info['extracted_chars']} of {total} chars]", info
        
        info.update(status='Full', extracted_chars=total)
        return txt, info
    except Exception as e:
        info.update(status='Error', error_message=str(e))
        return f"[Error reading {name}: {e}]", info

def generate_summary_table_md(data, summary_counts):
    """Generates a Markdown formatted summary table."""
    lines = ["## Extraction Summary\n"]
    
    lines.append(f"- Total files processed: {summary_counts['total_processed']}")
    lines.append(f"- Code files: {summary_counts['code_files']}")
    lines.append(f"- Data files: {summary_counts['data_files']}")
    lines.append(f"- Other text files: {summary_counts['other_text_files']}")
    lines.append(f"- Non-text files: {summary_counts['non_text_files']}")
    lines.append(f"- Files with errors: {summary_counts['error_files']}\n")
    
    header = ['File Path', 'Status', 'Details']
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + " :--- |".join([""]*(len(header)+1))) 

    for item in sorted(data, key=lambda x: x['relative_path']):
        rp = sanitize(item['relative_path'])
        st = item['status']
        
        disp_status = ''
        details = ''
        
        if st == 'Full':
            disp_status = 'Full'
            details = f"{item['total_chars']} chars"
        elif st == 'Partial':
            pct = int((item['extracted_chars'] / item['total_chars']) * 100) if item['total_chars'] and item['total_chars'] > 0 else 0
            disp_status = f'Partial ({pct}%)'
            details = f"{item['extracted_chars']} / {item['total_chars']} chars"
        elif st == 'Non-Text':
            disp_status = 'Non-Text'
            details = 'N/A'
        else: # Error
            disp_status = 'Error'
            details = item.get('error_message', '')[:80] # Truncate long error messages

        rp_md = rp.replace("|", "\\|") # Escape pipe characters for Markdown table
        details_md = str(details).replace("|", "\\|")

        lines.append(f"| `{rp_md}` | {disp_status} | {details_md} |")
    return "\n".join(lines)

def get_lang_hint(file_path, files_in_same_dir):
    """Determines a language hint for Markdown code blocks."""
    _, ext = os.path.splitext(file_path)
    lang_hint = ext[1:].lower() # Remove dot and lowercase

    if lang_hint in ["storyboard", "xib", "xcscheme", "entitlements", "plist"]:
        return "xml"
    if lang_hint == "mm":
        return "objective-c"
    if lang_hint == "podfile":
        return "ruby"
    if lang_hint == "cartfile" or lang_hint == "yml" or lang_hint == "yaml":
        return "yaml"
    if lang_hint == "h": # Try to guess C, C++, or Objective-C for .h files
        is_objc_header = any(f.endswith(('.m', '.mm')) for f in files_in_same_dir)
        if is_objc_header: return "objective-c"
        is_cpp_header = any(f.endswith(('.cpp', '.cxx', '.cc')) for f in files_in_same_dir)
        if is_cpp_header: return "cpp"
        return "c" # Default to C for .h if no stronger indicator
    if lang_hint == "hpp":
        return "cpp"
    if lang_hint == "pbxproj": # project.pbxproj
        return "text" # It's a property list; 'text' is safest. 'json' might be too specific.
    
    # Common languages that map directly
    if lang_hint in ["swift", "m", "c", "cpp", "json", "sh", "py", "rb", "js", "ts", 
                     "java", "kt", "go", "rs", "html", "css", "scss", "less", "php", 
                     "md", "txt"]:
        return lang_hint
        
    return "" # No hint if unknown

def generate_md_report(root_dir, output_md_path, 
                       max_code_len_cfg, max_data_len_cfg, max_pbxproj_len_cfg,
                       ignore_dirs_set_cfg, ignore_files_set_cfg,
                       code_ext_set_cfg, data_ext_set_cfg):
    """Generates the full Markdown report content and writes it to a file."""
    abs_root_dir = os.path.abspath(root_dir)
    project_name_sanitized = sanitize(os.path.basename(abs_root_dir))
    generation_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md_content_parts = []

    print(f"Starting Markdown report generation for: {project_name_sanitized}")

    # --- Metadata ---
    md_content_parts.append(f"# Xcode Project Report: {project_name_sanitized}")
    md_content_parts.append(f"\n*Generated: {generation_timestamp}*")
    md_content_parts.append(f"*Source: `{abs_root_dir}`*\n")

    # --- Directory Tree ---
    print("Generating directory tree...")
    md_content_parts.append(get_directory_tree_md(abs_root_dir, ignore_dirs_set_cfg, ignore_files_set_cfg))
    md_content_parts.append("\n---\n") # Horizontal rule

    # --- Summary Table ---
    file_summary_data = []
    all_files_in_project_structure = {} # To store siblings for lang_hint
    summary_stats = {
        'total_processed': 0, 'code_files': 0, 'data_files': 0,
        'other_text_files': 0, 'non_text_files': 0, 'error_files': 0
    }
    
    print("Analyzing files for summary...")
    for dirpath, dirnames, filenames_in_current_dir in os.walk(abs_root_dir, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs_set_cfg and not d.startswith('.')]
        all_files_in_project_structure[dirpath] = filenames_in_current_dir # Store siblings

        for filename in sorted(filenames_in_current_dir):
            if filename in ignore_files_set_cfg or filename.startswith('.'):
                continue
            
            summary_stats['total_processed'] += 1
            full_path = os.path.join(dirpath, filename)
            file_class = classify_file(full_path, code_ext_set_cfg, data_ext_set_cfg)
            
            _, status_info = get_file_content_and_status(
                full_path, max_code_len_cfg, max_data_len_cfg, max_pbxproj_len_cfg,
                code_ext_set_cfg, data_ext_set_cfg
            )
            status_info['relative_path'] = os.path.relpath(full_path, abs_root_dir)
            file_summary_data.append(status_info)

            # Update summary counts based on status and classification
            if status_info['status'] == 'Error':
                summary_stats['error_files'] += 1
            elif status_info['status'] == 'Non-Text':
                summary_stats['non_text_files'] += 1
            else: # It's some kind of text file
                if file_class == 'code':
                    summary_stats['code_files'] += 1
                elif file_class == 'data':
                    summary_stats['data_files'] += 1
                else: # Text file, but not classified as code/data by extension (e.g. .txt without specific rule)
                     summary_stats['other_text_files'] += 1
                     
    md_content_parts.append(generate_summary_table_md(file_summary_data, summary_stats))
    md_content_parts.append("\n---\n") # Horizontal rule

    # --- File Contents ---
    md_content_parts.append("## File Contents\n")
    print("Extracting and formatting file contents...")
    
    processed_files_for_content = 0
    for dirpath, dirnames, filenames_in_current_dir in os.walk(abs_root_dir, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs_set_cfg and not d.startswith('.')]
        filenames_in_current_dir.sort() # Ensure consistent order

        for filename in filenames_in_current_dir:
            if filename in ignore_files_set_cfg or filename.startswith('.'):
                continue
            
            processed_files_for_content += 1
            if processed_files_for_content % 20 == 0: # Progress update less frequently
                print(f"  Formatted content for {processed_files_for_content} files...")

            full_path = os.path.join(dirpath, filename)
            relative_path_sanitized = sanitize(os.path.relpath(full_path, abs_root_dir))
            
            content_text, status_info = get_file_content_and_status(
                full_path, max_code_len_cfg, max_data_len_cfg, max_pbxproj_len_cfg,
                code_ext_set_cfg, data_ext_set_cfg
            )
            
            md_content_parts.append(f"### File: `{relative_path_sanitized}`\n")

            if status_info['status'] == 'Non-Text' or status_info['status'] == 'Error':
                md_content_parts.append(f"```text\n{content_text}\n```\n")
            else: # Full or Partial text content
                parent_dir_of_file = os.path.dirname(full_path)
                sibling_files = all_files_in_project_structure.get(parent_dir_of_file, [])
                language_hint = get_lang_hint(filename, sibling_files)
                
                md_content_parts.append(f"```{language_hint}") # Start code block with lang hint
                md_content_parts.append(content_text)
                md_content_parts.append("```\n")

    # --- Write to file ---
    try:
        # Ensure output directory exists
        output_md_dir = os.path.dirname(output_md_path)
        if output_md_dir and not os.path.exists(output_md_dir): # Check if output_md_dir is not empty (i.e. not current dir)
            os.makedirs(output_md_dir)
            
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(md_content_parts))
        print(f"✅ Markdown report generated successfully: {output_md_path}")
    except IOError as e:
        print(f"Error writing Markdown report to file {output_md_path}: {e}")
        sys.exit(1)

# ─── MAIN EXECUTION WRAPPER ───────────────────────────────────────────────────
def main():
    """Parses arguments, sets up configuration, and calls the report generator."""
    parser = argparse.ArgumentParser(
        description="Generate an Xcode project (or general directory) report in Markdown format.",
        formatter_class=argparse.RawTextHelpFormatter # Allows for newlines in help text
    )
    parser.add_argument('project_path', 
                        help="Root directory of the project to report on.")
    parser.add_argument('output_md',  
                        help="Path where the output Markdown file will be saved (e.g., project_report.md).")
    
    # Max length arguments
    parser.add_argument('--max-code-length', type=int, default=DEFAULT_MAX_CODE_LEN,
                        help=f"Maximum characters for code files. Use -1 for unlimited. (Default: {DEFAULT_MAX_CODE_LEN})")
    parser.add_argument('--max-data-length', type=int, default=DEFAULT_MAX_DATA_LEN,
                        help=f"Maximum characters for data files. Use -1 for unlimited. (Default: {DEFAULT_MAX_DATA_LEN})")
    parser.add_argument('--max-pbxproj-length', type=int, default=DEFAULT_MAX_PBXPROJ_LEN,
                        help=f"Maximum characters for project.pbxproj file. Use -1 for unlimited. (Default: {DEFAULT_MAX_PBXPROJ_LEN})")
    
    # Configuration override arguments
    parser.add_argument('--ignore-dirs', type=str, default=None,
                        help="Comma-separated list of directory names to ignore (replaces default).\n"
                             f"Example: \".git,build\"\nDefault: \"{','.join(sorted(list(DEFAULT_IGNORE_DIRS)))}\"")
    parser.add_argument('--ignore-files', type=str, default=None,
                        help="Comma-separated list of exact file names to ignore (replaces default).\n"
                             f"Example: \".DS_Store,config.log\"\nDefault: \"{','.join(sorted(list(DEFAULT_IGNORE_FILES)))}\"")
    parser.add_argument('--code-exts', type=str, default=None,
                        help="Comma-separated list of extensions for 'code' files (replaces default).\n"
                             "Ensure extensions start with a dot, e.g., '.swift,.py'\n"
                             f"Default: \"{','.join(sorted(list(DEFAULT_CODE_EXT)))}\"")
    parser.add_argument('--data-exts', type=str, default=None,
                        help="Comma-separated list of extensions for 'data' files (replaces default).\n"
                             "Ensure extensions start with a dot, e.g., '.json,.xml'\n"
                             f"Default: \"{','.join(sorted(list(DEFAULT_DATA_EXT)))}\"")
    
    args = parser.parse_args()

    # --- Process Configuration from Arguments ---
    # If command-line arg is provided, use it; otherwise, use the default.
    # Ensure sets are used for efficient lookup.
    
    current_ignore_dirs = set(args.ignore_dirs.split(',')) if args.ignore_dirs is not None else DEFAULT_IGNORE_DIRS.copy()
    current_ignore_files = set(args.ignore_files.split(',')) if args.ignore_files is not None else DEFAULT_IGNORE_FILES.copy()
    
    if args.code_exts is not None:
        current_code_exts = set(e.strip().lower() if e.strip().startswith('.') else '.' + e.strip().lower() 
                                for e in args.code_exts.split(','))
    else:
        current_code_exts = DEFAULT_CODE_EXT.copy()

    if args.data_exts is not None:
        current_data_exts = set(e.strip().lower() if e.strip().startswith('.') else '.' + e.strip().lower()
                                for e in args.data_exts.split(','))
    else:
        current_data_exts = DEFAULT_DATA_EXT.copy()

    # --- Validate Paths ---
    if not os.path.isdir(args.project_path):
        print(f"Error: Project path '{args.project_path}' is not a valid directory.")
        sys.exit(1)
    
    output_md_dir = os.path.dirname(args.output_md)
    # Create output directory if it doesn't exist and if output_md specifies a directory
    if output_md_dir and not os.path.exists(output_md_dir):
        try:
            os.makedirs(output_md_dir)
            print(f"Created output directory: {output_md_dir}")
        except OSError as e:
            print(f"Error: Could not create output directory '{output_md_dir}': {e}")
            sys.exit(1)

    # --- Generate Report ---
    generate_md_report(
        args.project_path,
        args.output_md,
        args.max_code_length,
        args.max_data_length,
        args.max_pbxproj_length,
        current_ignore_dirs,
        current_ignore_files,
        current_code_exts,
        current_data_exts
    )

if __name__=='__main__':
    main()
