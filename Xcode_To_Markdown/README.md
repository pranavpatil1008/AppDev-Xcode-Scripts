# Project to Markdown Reporter

This Python script generates a comprehensive Markdown report from a given project directory, with a primary focus on Xcode projects. It includes a directory tree, a summary of processed files, and the sanitized content of text-based files, all formatted for Markdown. The script is configurable, allowing users to customize ignored directories/files, define file types, and set content length limits.

## Features

* **Directory Tree:** Generates a Markdown-formatted list representing the project's directory structure.
* **File Content Extraction:** Extracts and includes the content of text-based files (code, data, etc.) within Markdown code blocks.
    * Converts special characters (like '■') and normalizes Unicode accents to basic ASCII for clean Markdown output.
    * Replaces tabs with 4 spaces for consistent code formatting.
    * Attempts to provide language hints for Markdown code blocks based on file extensions.
* **Extraction Summary:** Provides a Markdown table summarizing all processed files, their status (Full, Partial, Non-Text, Error), and character counts.
* **Configurable Filters:**
    * Ignore specific directories (e.g., `.git`, `build`, `Pods`).
    * Ignore specific files (e.g., `.DS_Store`, `Podfile.lock`).
    * Define custom sets of file extensions for "code" and "data" files, which can have different content length limits.
* **Content Length Limits:** Set maximum character limits for extracted code, data, and `project.pbxproj` files to keep the Markdown manageable (unlimited option available).
* **Markdown Output:** Generates a single Markdown file with:
    * A title page (project name, generation date, source path).
    * The directory tree.
    * The file extraction summary table.
    * Detailed content of each extracted file, formatted in code blocks.

## Requirements

* Python 3.x

## Usage

The script is run from the command line.

```bash
python xcode_to_markdown.py <project_path> <output_md_path> [options]


