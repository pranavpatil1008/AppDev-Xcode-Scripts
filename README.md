# AppDev-Xcode-Scripts

Welcome to **AppDev-Xcode-Scripts**! This repository is a collection of Python scripts designed to assist developers working with Xcode projects and targeting Apple platforms (iOS, macOS, watchOS, tvOS). The goal is to provide useful utilities that can help streamline workflows, automate tasks, and offer better insights into project structures.

## About This Collection

As developers, we often encounter repetitive tasks or need specific information that isn't easily accessible. The scripts in this repository aim to address some of these common needs. Whether it's generating documentation, understanding project composition, or other development aids, we hope you find these tools helpful.

## Scripts Included

Below is a list of the scripts currently available in this repository. Each script resides in its own subdirectory, which contains the script itself and a dedicated `README.md` file with detailed information about its purpose, requirements, usage, and any specific considerations.

1.  **[Xcode Project Tree Generator](./Xcode_Project_Tree/README.md)**
    * Generates a textual tree-like view of an Xcode project's navigator structure. It intelligently handles both virtual (yellow) groups and synchronized (blue) folder references by scanning the file system for the latter, aiming to accurately mirror what you see in the Xcode Project Navigator.

2.  **[Xcode Project to PDF Reporter](./Xcode_Project_To_PDF/README.md)**
    * Creates a comprehensive PDF report from a given project directory (primarily focused on Xcode projects). The report includes a directory tree, a summary of extracted files, and the sanitized content of text-based files. It's configurable for ignored items, file types, and content length limits.

3.  **[Xcode Project to Markdown Reporter](./Xcode_To_Markdown/README.md)**
    * Generates a detailed Markdown report from a project directory. Similar to the PDF reporter, it includes a directory tree, file summary, and sanitized file contents formatted for Markdown, with language hints for code blocks. It's also configurable.

*(More scripts may be added in the future!)*

## General Requirements

* **Python 3.x** is required to run these scripts.
* Specific Python libraries (e.g., `python-pbxproj`, `reportlab`, `pillow`) may be needed for individual scripts. Please refer to the `README.md` file within each script's subdirectory for its particular dependencies and installation instructions.

## Getting Started

1.  Clone this repository:
    ```bash
    git clone [https://github.com/pranavpatil1008/AppDev-Xcode-Scripts.git](https://github.com/pranavpatil1008/AppDev-Xcode-Scripts.git)
    ```
    *(Replace `pranavpatil1008` with your actual GitHub username if different, once the repository is public).*
2.  Navigate to the subdirectory of the script you wish to use.
3.  Follow the instructions in that script's specific `README.md` file for setup and execution.

## Contributing

Contributions, bug reports, and feature requests are welcome! If you have a script you'd like to add or an improvement to an existing one, please feel free to:

1.  Fork the repository.
2.  Create a new branch for your feature or fix.
3.  Make your changes.
4.  Submit a pull request with a clear description of your changes.

Please check the [issues page](https://github.com/pranavpatil1008/AppDev-Xcode-Scripts/issues) *(update URL after repo creation)* for existing issues or to open a new one.

## License

This project and its scripts are licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

