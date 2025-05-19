# Xcode Project to PDF Reporter

This Python script generates a comprehensive PDF report from a given project directory, with a primary focus on Xcode projects. It includes a directory tree, a summary of extracted files, and the sanitized content of text-based files. The script is designed to be configurable, allowing users to customize ignored directories/files, define file types, and set content length limits.

## Features

* **Directory Tree:** Generates a textual representation of the project's directory structure.
* **File Content Extraction:** Extracts and includes the content of text-based files (code, data, etc.).
    * Converts special characters (like '■') and normalizes Unicode accents to basic ASCII for clean PDF output.
    * Replaces tabs with 4 spaces for consistent code formatting.
* **Extraction Summary:** Provides a table summarizing all processed files, their status (Full, Partial, Non-Text, Error), and character counts.
* **Configurable Filters:**
    * Ignore specific directories (e.g., `.git`, `build`, `Pods`).
    * Ignore specific files (e.g., `.DS_Store`, `Podfile.lock`).
    * Define custom sets of file extensions for "code" and "data" files, which can have different content length limits.
* **Content Length Limits:** Set maximum character limits for extracted code and data files to keep the PDF manageable (unlimited option available).
* **Dependency Management:** Automatically attempts to install required Python libraries (`reportlab`, `pillow`) if they are not found (can be disabled).
* **PDF Output:** Generates a multi-page PDF document with:
    * A title page (project name, generation date, source path).
    * The directory tree.
    * The file extraction summary table.
    * Detailed content of each extracted file.

## Requirements

* Python 3.x
* **ReportLab** library (`pip install reportlab`)
* **Pillow** library (`pip install Pillow`) (Pillow is a dependency of ReportLab for image handling, good to ensure it's available)

## Installation of Dependencies

The script will attempt to automatically install `reportlab` and `pillow` using pip if they are not detected in your Python environment. This requires pip to be available and an internet connection.

To disable this automatic installation (e.g., in restricted environments or if you prefer to manage packages manually), you can use the `--no-auto-install` flag when running the script. If you use this flag and the libraries are missing, the script will exit with an error message prompting you to install them.

Manual installation:
```bash
pip install reportlab pillow
# or for a specific python environment, e.g., python3.9 -m pip install ...

UsageThe script is run from the command line.python xcode_project_to_pdf.py <project_path> <output_pdf_path> [options]


