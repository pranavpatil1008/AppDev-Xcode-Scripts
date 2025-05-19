# Xcode Project Tree Generator

This Python script generates a textual tree-like representation of an Xcode project's navigator structure. It aims to mirror the visual hierarchy seen in Xcode's Project Navigator, including handling both virtual (yellow) groups and synchronized (blue) folder references by scanning the file system for the latter.

## Features

* **Xcode Project Parsing:** Reads the `.xcodeproj` file to understand its internal structure.
* **Handles Different Group Types:**
    * **Virtual Groups (Yellow Folders):** Displays files and subgroups as defined explicitly in the `project.pbxproj` file.
    * **Synchronized Folders/Folder References (Blue Folders):**
        * Identifies groups linked to file system directories (often `PBXFileSystemSynchronizedRootGroup` or `PBXGroup` with a `path`).
        * Resolves the disk path for these synchronized groups.
        * **Scans the actual file system directory** to list its contents (files and subfolders), providing an accurate view of what Xcode would dynamically display.
* **Target Awareness (Basic):**
    * Identifies build targets within the project.
    * For synchronized groups that also represent a target (e.g., a framework or app extension module), it attempts to list files from the file system first.
    * If a synchronized group's folder is empty or no recognizable files are found, it will try to list the product of the associated target (e.g., `MyFramework.framework`).
    * Lists files found in the `PBXSourcesBuildPhase` for targets that appear directly in the tree (though this can be limited by what the `pbxproj` library reports, especially for targets whose sources are primarily managed by synchronized folders).
* **Iconography:** Uses simple emoji icons to denote group types, file types, and targets for better readability:
    * `🗂️`: Virtual (yellow) group
    * `🔗`: Synchronized (blue) folder reference / `PBXFileSystemSynchronizedRootGroup`
    * `🟦`: Other blue folder references (if not a `PBXFileSystemSynchronizedRootGroup` but still path-based)
    * `📄`: Generic file
    * `𝑺`: Swift file
    * `𝒉`: Header file (.h, .hpp)
    * `𝒎`: Implementation file (.m, .mm, .c, .cpp)
    * `🎨`: Asset Catalog (.xcassets)
    * `⚙️`: Info.plist file
    * `｛｝`: JSON file
    * `💡`: Intent Definition file
    * `🌍`: Localized resources/group (.strings, .stringsdict, PBXVariantGroup)
    * `🔑`: Entitlements file
    * `📱`: Storyboard or XIB file
    * `🖼️`: Common image files
    * `📰`: PDF file
    * `🎈`: Playground file
    * `🎯`: Build Target
    * `➡️`: Product of a target
* **Automatic Project Detection:**
    * Assumes the script is placed in a `Scripts` subdirectory at the root of your Xcode project.
    * It will try to find the `.xcodeproj` file in the parent directory.
    * Includes a fallback to infer the project name if the script's parent folder is named after the project (e.g., `MyProject/Scripts/` and `MyProject/MyProject.xcodeproj`).

## Requirements

* Python 3.x
* `python-pbxproj` library:
    * The script relies on this library to parse the `.xcodeproj` file.
    * Install it via pip: `pip install pbxproj` (or `pip3 install pbxproj`)

## Setup and Usage

1.  **Placement:**
    * The script is designed to be placed in a subdirectory named `Scripts` directly within your main Xcode project folder.
        ```
        YourXcodeProject/
        ├── YourXcodeProject.xcodeproj
        ├── YourMainAppFolder/
        ├── YourFrameworkFolder/
        └── Scripts/
            └── xcode_tree.py  <-- Place script here
        ```
    * If placed elsewhere, the automatic project path detection might not work, and you may need to modify the path configuration section in the script.

2.  **Ensure Dependencies:**
    * Make sure you have Python 3 and the `python-pbxproj` library installed in the Python environment you'll use to run the script.

3.  **Run from Terminal:**
    * Navigate to the directory containing the script (or use its full path).
    * Execute the script using your Python 3 interpreter. For example, if you used Homebrew to install a specific Python version (like `python3.9`) that has `pbxproj` installed:
        ```bash
        # If in the Scripts directory:
        /opt/homebrew/bin/python3.9 xcode_tree.py
        ```
        or
        ```bash
        # Using the full path to the script:
        /opt/homebrew/bin/python3.9 "/Users/yourname/Documents/Xcode/YourProject/Scripts/xcode_tree.py"
        ```
        Replace `/opt/homebrew/bin/python3.9` with the actual path to your Python 3 interpreter if needed (e.g., just `python3`).

## Output

The script will print the Xcode project's logical structure to the console, similar to this (example structure):


Xcode Project Structure for: YourProject.xcodeproj
🗂️ Unnamed PBXGroup 🔗 YourMainAppFolder 📁 Views 𝑺 LoginView.swift 📁 Controllers 𝑺 LoginViewController.swift 𝑺 AppDelegate.swift 🔗 YourFrameworkFolder 📁 Sources 𝑺 MyFrameworkClass.swift 📁 Resources 🎨 Assets.xcassets 🔗 YourTestTargetFolder 𝑺 YourTests.swift 🗂️ Frameworks 📄 SomeFramework.framework 🗂️ Products 📄 YourMainApp.app 📄 YourFramework.framework

## Known Limitations & Considerations

* **Reliance on `python-pbxproj`:** The initial parsing of the `.xcodeproj` file depends on the `python-pbxproj` library. If this library has issues parsing certain aspects of a very complex or new Xcode project format, the script's accuracy might be affected.
    * We observed that for some targets managed by synchronized folders, `python-pbxproj` v4.2.1 reported their "Compile Sources" build phase as empty. This script now primarily relies on file system scanning for such synchronized groups.
* **File System Access:** For synchronized folder references (blue folders), the script needs read access to the corresponding directories on your file system to list their contents.
* **Path Resolution for Synchronized Groups:** The script makes a best effort to resolve the disk paths for synchronized groups, especially if their `sourceTree` attribute is reported as `None` by the library (it assumes `SOURCE_ROOT` in such cases for top-level project items). This heuristic works well for many common project setups.
* **Xcode's Dynamic Nature:** Xcode performs some dynamic processing when displaying the Project Navigator (e.g., applying specific filter rules or exceptions defined on synchronized groups). This script provides a structural representation based on the `.pbxproj` data and direct file system scanning, which might not capture every single dynamic display nuance of the Xcode IDE.
* **Icons:** The emoji icons are for general guidance and might not cover every file type or Xcode-specific bundle perfectly.

## License

This script is part of the `AppDev_Xcode_Scripts` (or your chosen repository name) repository, licensed under the MIT License. Please see the main `LICENSE` file in the root of the repository.

## Issues and Contributions

If you encounter issues or have suggestions for improvement, please open an issue in the main repository.

