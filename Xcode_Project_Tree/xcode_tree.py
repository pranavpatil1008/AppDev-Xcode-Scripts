#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xcode Project Tree Generator
Generates a textual tree representation of an Xcode project's navigator structure,
including resolving synchronized folder references by scanning the file system.
"""

import os
import sys
from pathlib import Path # For easier path manipulation and directory scanning
from pbxproj import XcodeProject

# --- Configuration ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assumes the script is in a 'Scripts' subdirectory of your project root.
    # e.g., YourProject/Scripts/Xcode_tree.py
    # YourProject/YourProject.xcodeproj
    project_root_dir = os.path.dirname(script_dir) 
    
    xcodeproj_name = None
    for item in os.listdir(project_root_dir):
        if item.endswith(".xcodeproj"):
            xcodeproj_name = item
            break
    
    if not xcodeproj_name:
        # Fallback: try to infer from the parent directory name if script is directly in project dir
        project_folder_name = os.path.basename(project_root_dir)
        potential_xcodeproj = f"{project_folder_name}.xcodeproj"
        if os.path.exists(os.path.join(project_root_dir, potential_xcodeproj)):
            xcodeproj_name = potential_xcodeproj
        # Specific fallback for your project name if others fail
        elif os.path.basename(project_root_dir) == "Eleve" and \
             os.path.exists(os.path.join(project_root_dir, "Eleve.xcodeproj")): # Match user's project name
            xcodeproj_name = "Eleve.xcodeproj"
        else:
            print(f"Error: Could not automatically find an .xcodeproj directory in {project_root_dir}")
            print("       Please ensure the script is in a 'Scripts' subdirectory of your project root,")
            print("       or that your main project folder is named such that 'YourFolder/YourFolder.xcodeproj' exists.")
            sys.exit(1)

    xcodeproj_path = os.path.join(project_root_dir, xcodeproj_name)
    # project_root_dir is used to resolve SOURCE_ROOT paths
except Exception as e:
    print(f"Error determining project path: {e}")
    print("Please ensure the script is placed correctly.")
    sys.exit(1)
# --- End Configuration ---

TARGETS_BY_NAME_CACHE = {} # Cache for PBXNativeTarget objects by name

def get_display_name(obj):
    """Gets the display name for an Xcode project item, preferring path for blue folders if name is just basename."""
    name = getattr(obj, 'name', None)
    path = getattr(obj, 'path', None)
    if name:
        # For groups that are folder references (blue folders), path might be more descriptive
        # if the name is just the last component of that path.
        if path and obj.isa in ['PBXGroup', 'PBXFileSystemSynchronizedRootGroup'] and \
           getattr(obj, 'source_tree', 'GROUP') != 'GROUP' and name == os.path.basename(path):
            return path 
        return name
    elif path:
        # For file references, path is often just the filename.
        # For groups without a name, path might be the folder name.
        return os.path.basename(path) 
    elif hasattr(obj, 'isa'):
        return f"Unnamed {obj.isa}" # Fallback if no name or path
    return "Unknown Item"

def get_resolved_path_for_group_item(project, item_obj, current_project_root_dir):
    """
    Resolves the filesystem path for a PBXFileReference or PBXGroup.
    Returns an absolute path or None if not resolvable.
    """
    path = getattr(item_obj, 'path', None)
    source_tree = getattr(item_obj, 'source_tree', None) 
    # item_display_name = get_display_name(item_obj) # For debug clarity

    # print(f"# DEBUG_PATH: Trying to resolve path for '{item_display_name}' (ISA: {item_obj.isa}). Path='{path}', SourceTree='{source_tree}'")

    if not path: 
        # print(f"# DEBUG_PATH: Path attribute is missing or empty for '{item_display_name}'. Cannot resolve.")
        return None

    effective_source_tree = source_tree
    # If sourceTree is None (or the string "None") for an item that has a path,
    # and it's a group type likely at the top level, assume SOURCE_ROOT.
    # This was crucial for projects where 'sourceTree' isn't explicitly set for top-level synced folders.
    if (source_tree is None or source_tree == 'None') and \
       item_obj.isa in ['PBXGroup', 'PBXFileSystemSynchronizedRootGroup']:
        # print(f"# DEBUG_PATH: SourceTree for '{item_display_name}' is '{source_tree}'. Assuming SOURCE_ROOT for path '{path}'.")
        effective_source_tree = 'SOURCE_ROOT'
    
    if not effective_source_tree: # If still no effective source_tree after potential default
        # print(f"# DEBUG_PATH: Effective SourceTree is still missing for '{item_display_name}'. Cannot resolve.")
        return None

    if effective_source_tree == 'SOURCE_ROOT':
        resolved = os.path.abspath(os.path.join(current_project_root_dir, path))
        # print(f"# DEBUG_PATH: Resolved '{item_display_name}' (SOURCE_ROOT) to: {resolved}")
        return resolved
    elif effective_source_tree == '<group>':
        parent_id = getattr(item_obj, 'parent', None)
        if parent_id:
            parent_obj = project.get_object(parent_id)
            if parent_obj:
                # print(f"# DEBUG_PATH: Group '{item_display_name}' is relative to parent '{get_display_name(parent_obj)}'. Resolving parent path...")
                parent_full_path = get_resolved_path_for_group_item(project, parent_obj, current_project_root_dir)
                if parent_full_path and os.path.isdir(parent_full_path):
                    resolved = os.path.abspath(os.path.join(parent_full_path, path))
                    # print(f"# DEBUG_PATH: Resolved '{item_display_name}' (<group>) to: {resolved}")
                    return resolved
                # else:
                    # print(f"# DEBUG_PATH: Parent path for '{item_display_name}' not resolvable or not a directory: {parent_full_path}")
        # print(f"# DEBUG_PATH: <group> for '{item_display_name}' - trying fallback relative to project root as parent resolution failed or no parent.")
        resolved = os.path.abspath(os.path.join(current_project_root_dir, path))
        # print(f"# DEBUG_PATH: Resolved '{item_display_name}' (<group> fallback) to: {resolved}")
        return resolved
    elif effective_source_tree == '<absolute>':
        resolved = os.path.abspath(path)
        # print(f"# DEBUG_PATH: Resolved '{item_display_name}' (<absolute>) to: {resolved}")
        return resolved
    else:
        # print(f"# DEBUG_PATH: Unhandled effective_source_tree '{effective_source_tree}' for path resolution of '{item_display_name}'. Cannot resolve.")
        return None

def print_filesystem_tree_for_synced_group(directory_path, indent_level):
    """
    Prints a tree of recognized source/resource files and folders from a given filesystem directory.
    """
    # print(f"# DEBUG_SCAN: Attempting FS scan for synced group at: {directory_path}")
    source_extensions = [ # More comprehensive list of extensions
        '.swift', '.m', '.mm', '.c', '.cpp', '.h', '.hpp', 
        '.storyboard', '.xib', '.plist', '.json',         
        '.xcassets', '.dataset', '.mlmodel', '.playground', # Bundles treated as files
        '.intentdefinition', '.strings', '.stringsdict',   
        '.entitlements', '.md', '.txt', '.rtf',
        '.png', '.jpg', '.jpeg', '.gif', '.heic', '.svg', '.pdf', 
        '.ttf', '.otf', 
        '.wav', '.mp3', '.aac', '.m4a' 
    ]
    initial_indent_str = "  " * indent_level
    
    if not directory_path or not os.path.isdir(directory_path):
        # This case should ideally be handled by the caller, but as a safeguard:
        # print(f"{initial_indent_str}⚠️ Path not found or not a directory for FS scan: {directory_path}")
        return False # Indicate no files were found or path was bad

    found_any_recognizable_items = False
    
    items_to_print = []
    try:
        for item_name in sorted(os.listdir(directory_path)):
            # Skip common hidden files/folders and build artifacts
            if item_name.startswith('.') or item_name in ['__pycache__', 'build', 'DerivedData']: 
                continue
            item_path = os.path.join(directory_path, item_name)
            is_dir = os.path.isdir(item_path)
            items_to_print.append({'name': item_name, 'path': item_path, 'is_dir': is_dir})
    except Exception as e:
        # print(f"{initial_indent_str}⚠️ Error listing directory {directory_path}: {e}")
        return False

    # if not items_to_print and indent_level > 0: 
        # print(f"# DEBUG_SCAN: Directory '{directory_path}' is empty or contains only hidden/ignored files/folders.")

    for item in items_to_print:
        item_name = item['name']
        item_path = item['path']
        is_dir = item['is_dir']
        
        if is_dir:
            # Special handling for bundles that look like files in Xcode
            if item_name.endswith(".xcassets"):
                print(f"{initial_indent_str}🎨 {item_name}")
                found_any_recognizable_items = True
            elif item_name.endswith(".playground"):
                print(f"{initial_indent_str}🎈 {item_name}") 
                found_any_recognizable_items = True
            # Add other bundle types here if needed (e.g., .xcdatamodeld)
            else:
                print(f"{initial_indent_str}📁 {item_name}")
                found_any_recognizable_items = True 
                # Recurse for subdirectories
                print_filesystem_tree_for_synced_group(item_path, indent_level + 1)
        else: # It's a file
            file_ext = Path(item_name).suffix.lower()
            # Check if the extension is in our list of source_extensions
            is_recognized_file = any(item_name.endswith(ext) for ext in source_extensions)

            if is_recognized_file:
                found_any_recognizable_items = True
                icon = "📄" # Default file icon
                if file_ext == ".swift": icon = "𝑺"
                elif file_ext in (".h", ".hpp"): icon = "𝒉"
                elif file_ext in (".m", ".mm", ".c", ".cpp"): icon = "𝒎"
                elif file_ext == ".json": icon = "｛｝"
                elif file_ext == ".plist": icon = "⚙️"
                elif file_ext == ".intentdefinition": icon = "💡"
                elif file_ext == ".strings" or file_ext == ".stringsdict": icon = "🌍"
                elif file_ext == ".entitlements": icon = "🔑"
                elif file_ext in (".storyboard", ".xib"): icon = "📱"
                elif file_ext in (".png", ".jpg", ".jpeg", ".gif", ".heic", ".svg"): icon = "🖼️"
                elif file_ext == ".pdf": icon = "📰"
                # Add more specific icons as needed
                print(f"{initial_indent_str}{icon} {item_name}")
            # else:
                # print(f"# DEBUG_SCAN: Skipping file (not in recognized extensions): {item_name} in {directory_path}")

    return found_any_recognizable_items

def print_target_files_from_buildphase(project, target_obj, indent_level_for_files):
    """
    Prints source files from a target's PBXSourcesBuildPhase.
    This is now primarily a fallback if FS scan for a synced group associated with this target yields nothing.
    Returns True if any source file was printed, False otherwise.
    """
    target_name_for_debug = get_display_name(target_obj)
    file_indent_str = "  " * indent_level_for_files
    any_source_files_printed = False # Specifically track if source files were printed
    
    build_phases = getattr(target_obj, 'buildPhases', [])
    for build_phase_id in build_phases:
        build_phase = project.get_object(build_phase_id)
        if build_phase and build_phase.isa == 'PBXSourcesBuildPhase':
            phase_files = getattr(build_phase, 'files', [])
            # if not phase_files:
                # print(f"# INFO: PBXSourcesBuildPhase for '{target_name_for_debug}' has an empty 'files' list (as per pbxproj library).")
            
            for build_file_id in phase_files: # This loop won't run if phase_files is empty
                build_file = project.get_object(build_file_id)
                if build_file and hasattr(build_file, 'fileRef') and build_file.fileRef:
                    file_ref = project.get_object(build_file.fileRef)
                    if file_ref:
                        any_source_files_printed = True 
                        file_display_name = get_display_name(file_ref)
                        file_icon = "📄"; 
                        if file_display_name.endswith(".swift"): file_icon = "𝑺"
                        # Add more icon logic if needed
                        print(f"{file_indent_str}{file_icon} {file_display_name} (from build phase)")
            break # Typically only one main sources phase to process for this purpose
    
    # If no source files were printed from the build phase, then print the product
    if not any_source_files_printed:
        product_ref_id = getattr(target_obj, 'productReference', None)
        if product_ref_id:
            product_ref = project.get_object(product_ref_id)
            if product_ref:
                print(f"{file_indent_str}➡️ Product: {get_display_name(product_ref)}")
    return any_source_files_printed

def print_project_structure(project_file_bundle_path, project_root_for_paths):
    """Loads the Xcode project and initiates the recursive printing of its structure."""
    global TARGETS_BY_NAME_CACHE
    TARGETS_BY_NAME_CACHE = {} # Reset cache for each call

    pbxproj_file_path = os.path.join(project_file_bundle_path, 'project.pbxproj')
    if not os.path.exists(pbxproj_file_path):
        print(f"Error: project.pbxproj not found at {pbxproj_file_path}"); return
    try:
        project = XcodeProject.load(pbxproj_file_path)
    except Exception as e:
        print(f"Error loading project '{pbxproj_file_path}': {e}"); return

    # Get the main PBXProject object
    if not hasattr(project, 'rootObject'): print(f"Error: Project lacks 'rootObject'"); return
    root_object_id = project.rootObject
    if not root_object_id: print(f"Error: Project's rootObject ID missing"); return
    project_obj = project.get_object(root_object_id) 
    if not project_obj : # Fallback, though get_object should work if ID is valid
         if root_object_id in project.objects: project_obj = project.objects[root_object_id]
    if not project_obj: print(f"Error: Could not retrieve root PBXProject object"); return
    if not hasattr(project_obj, 'isa') or project_obj.isa != 'PBXProject':
        print(f"Error: Root object is not PBXProject. ISA: '{getattr(project_obj, 'isa', 'N/A')}'"); return

    # Cache all native targets by name for quick lookup
    if hasattr(project_obj, 'targets'):
        # print("# DEBUG: Populating TARGETS_BY_NAME_CACHE...") # Optional: Keep this if needed for new projects
        for target_id in project_obj.targets:
            target = project.get_object(target_id)
            # Ensure we only cache PBXNativeTarget objects
            if target and hasattr(target, 'isa') and target.isa == 'PBXNativeTarget':
                target_name = get_display_name(target)
                TARGETS_BY_NAME_CACHE[target_name] = target
                # print(f"# DEBUG:   Cached target: '{target_name}'")
        # print(f"# DEBUG: TARGETS_BY_NAME_CACHE populated with {len(TARGETS_BY_NAME_CACHE)} native targets.")
    
    # Get the main group (root of the Project Navigator tree)
    main_group_id = project_obj.mainGroup
    if not main_group_id: print(f"Error: mainGroup ID missing"); return
    main_group = project.get_object(main_group_id)
    if not main_group: print(f"Error: Could not retrieve main group"); return

    print(f"Xcode Project Structure for: {os.path.basename(project_file_bundle_path)}")
    print("----------------------------------------------------")
    _print_recursive(project, main_group, 0, project_root_for_paths) # Pass project_root_for_paths
    print("----------------------------------------------------")

def _print_recursive(project, current_item, indent_level, current_project_root_dir):
    """Recursively prints the project structure."""
    global TARGETS_BY_NAME_CACHE
    display_name = get_display_name(current_item)
    icon = "❔" # Default icon
    indent_prefix = "  " * indent_level

    if current_item.isa == 'PBXGroup' or current_item.isa == 'PBXFileSystemSynchronizedRootGroup':
        is_synced_group = current_item.isa == 'PBXFileSystemSynchronizedRootGroup'
        
        if is_synced_group: icon = "🔗" # Link icon for Synced Group
        elif hasattr(current_item, 'path') and current_item.path and getattr(current_item, 'source_tree', '<group>') != '<group>': icon = "🟦" # Blue folder reference
        else: icon = "🗂️" # Yellow virtual group
        print(f"{indent_prefix}{icon} {display_name}")

        # For regular (yellow) groups, process children explicitly listed in the pbxproj
        # For synced groups, we prioritize filesystem scan below.
        if not is_synced_group and hasattr(current_item, 'children') and current_item.children:
            # print(f"# DEBUG_RECURSE: Regular Group '{display_name}' has {len(current_item.children)} pbxproj children.")
            for child_id in current_item.children:
                child_obj = project.get_object(child_id)
                if child_obj:
                    _print_recursive(project, child_obj, indent_level + 1, current_project_root_dir)
        
        # For synchronized groups (blue folders / PBXFileSystemSynchronizedRootGroup), scan the filesystem
        if is_synced_group:
            # print(f"# DEBUG_SYNC_GROUP_MAIN: Processing Synced Group: '{display_name}' (ISA: {current_item.isa})")
            group_fs_path = get_resolved_path_for_group_item(project, current_item, current_project_root_dir)
            # print(f"# DEBUG_SYNC_GROUP_MAIN: Resolved path for '{display_name}': {group_fs_path}") 

            if group_fs_path and os.path.isdir(group_fs_path):
                # print(f"# DEBUG_SYNC_GROUP_MAIN: Attempting FS scan for '{display_name}' at '{group_fs_path}'")
                filesystem_files_found = print_filesystem_tree_for_synced_group(group_fs_path, indent_level + 1)
                
                # If filesystem scan was empty OR found no recognized files, 
                # then try to print the associated target's product as a fallback.
                if not filesystem_files_found: 
                    # print(f"# DEBUG_SYNC_GROUP_MAIN: FS scan for '{display_name}' empty or no recognized files. Checking for associated target product.")
                    actual_target_to_process = None
                    potential_target_name_1 = display_name
                    potential_target_name_2 = display_name + "Extension" # Heuristic for widgets

                    if potential_target_name_1 in TARGETS_BY_NAME_CACHE:
                        actual_target_to_process = TARGETS_BY_NAME_CACHE[potential_target_name_1]
                    elif potential_target_name_2 in TARGETS_BY_NAME_CACHE:
                        actual_target_to_process = TARGETS_BY_NAME_CACHE[potential_target_name_2]
                    
                    if actual_target_to_process:
                        product_ref_id = getattr(actual_target_to_process, 'productReference', None)
                        if product_ref_id:
                            product_ref = project.get_object(product_ref_id)
                            if product_ref:
                                print(f"{'  ' * (indent_level + 1)}➡️ Product: {get_display_name(product_ref)}")
            # elif group_fs_path: # Path was resolved but not a directory
            #      print(f"# DEBUG_SYNC_GROUP_MAIN: Resolved path for '{display_name}' is NOT a directory: {group_fs_path}")
            # else: # Path resolution failed
            #      print(f"# DEBUG_SYNC_GROUP_MAIN: Could NOT resolve filesystem path for '{display_name}'. Fallback to target product.")
            #      # Fallback logic for when path resolution itself fails for a synced group
            #      actual_target_to_process = None
            #      potential_target_name_1 = display_name
            #      potential_target_name_2 = display_name + "Extension"
            #      if potential_target_name_1 in TARGETS_BY_NAME_CACHE: actual_target_to_process = TARGETS_BY_NAME_CACHE[potential_target_name_1]
            #      elif potential_target_name_2 in TARGETS_BY_NAME_CACHE: actual_target_to_process = TARGETS_BY_NAME_CACHE[potential_target_name_2]
            #      if actual_target_to_process:
            #          # This would call the function that relies on PBXSourcesBuildPhase.files, which we know is problematic
            #          # print_target_files_from_buildphase(project, actual_target_to_process, indent_level + 1)
            #          # Instead, just print product if path resolution failed for a synced group
            #          product_ref_id = getattr(actual_target_to_process, 'productReference', None)
            #          if product_ref_id:
            #              product_ref = project.get_object(product_ref_id)
            #              if product_ref: print(f"{'  ' * (indent_level + 1)}➡️ Product (path error): {get_display_name(product_ref)}")


    elif current_item.isa == 'PBXFileReference':
        icon = "📄" # Default file icon
        if display_name.endswith(".swift"): icon = "𝑺"
        elif display_name.endswith((".h", ".hpp")): icon = "𝒉"
        elif display_name.endswith((".m", ".mm", ".c", ".cpp")): icon = "𝒎"
        elif display_name.endswith((".png", ".jpg", ".jpeg", ".gif", ".heic")): icon = "🖼️"
        elif display_name.endswith(".json"): icon = "｛｝"
        elif display_name.endswith(".plist"): icon = "⚙️"
        elif display_name.endswith(".xcassets"): icon = "🎨" # Treat as a file-like bundle
        elif display_name.endswith((".storyboard", ".xib")): icon = "📱"
        elif display_name.endswith(".intentdefinition"): icon = "💡"
        elif display_name.endswith(".strings") or display_name.endswith(".stringsdict"): icon = "🌍"
        elif display_name.endswith(".entitlements"): icon = "🔑"
        elif display_name.endswith(".pdf"): icon = "📰"
        elif display_name.endswith(".playground"): icon = "🎈"
        # Add more icons as needed
        print(f"{indent_prefix}{icon} {display_name}")

    elif current_item.isa == 'PBXVariantGroup': # For localized files (e.g., Localizable.strings folder)
        icon = "🌍"
        print(f"{indent_prefix}{icon} {display_name} (Localized Group)")
        if hasattr(current_item, 'children') and current_item.children:
            for child_id in current_item.children:
                child_obj = project.get_object(child_id)
                if child_obj: # These children are usually PBXFileReference for each language
                    _print_recursive(project, child_obj, indent_level + 1, current_project_root_dir)
    
    elif current_item.isa == 'PBXNativeTarget': # If a target object itself appears directly in the tree
        target_name = get_display_name(current_item)
        print(f"{indent_prefix}🎯 {target_name} (Target - direct tree entry)")
        # Attempt to list its source files from build phase (might be empty as we've seen)
        # and then its product if no source files.
        print_target_files_from_buildphase(project, current_item, indent_level + 1) 
    
    else: # Fallback for any other ISA types not specifically handled
        # This helps identify if there are other object types appearing in the tree
        print(f"{indent_prefix}{icon} {display_name} (Type: {current_item.isa})")

if __name__ == "__main__":
    # --- Optional: Python Environment Debugging (Keep commented unless needed) ---
    # print("--- Python Debug Info ---")
    # print(f"Python version: {sys.version.splitlines()[0]}")
    # print(f"Python executable: {sys.executable}")
    # print("sys.path entries:")
    # for p_entry in sys.path:
    #     print(f"  {p_entry}")
    # if 'pbxproj' in sys.modules and hasattr(pbxproj, '__file__'):
    #     print(f"pbxproj module loaded from: {pbxproj.__file__}")
    # else:
    #     print("pbxproj module location not determined or module not loaded at debug print time.")
    # print("--- End Debug Info ---\n")
    # --- End Debugging ---

    if not os.path.exists(xcodeproj_path):
        print(f"Error: Xcode project path not found: {xcodeproj_path}")
        if 'script_dir' in locals(): # Check if these variables are defined before trying to print them
             print(f"       Script directory: {script_dir}")
        if 'project_root_dir' in locals():
             print(f"       Project root (derived): {project_root_dir}")
        sys.exit(1)
    
    # Pass the determined project_root_dir for path resolutions
    print_project_structure(xcodeproj_path, project_root_dir)

