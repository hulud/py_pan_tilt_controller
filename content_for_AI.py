import os


def generate_file_tree(root_dir):
    """
    Generate a string representing the file tree of root_dir and its subfolders.
    """
    tree_lines = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Calculate the depth of the current directory relative to the root
        depth = dirpath[len(root_dir):].count(os.sep)
        indent = ' ' * 4 * depth
        # Use the directory's basename unless we're at the root.
        current_dir = os.path.basename(dirpath) if os.path.basename(dirpath) else root_dir
        tree_lines.append(f"{indent}{current_dir}/")
        for filename in filenames:
            tree_lines.append(f"{indent}    {filename}")
    return "\n".join(tree_lines)


def read_root_files(root_dir, extensions, exclude_files=None):
    """
    Read the content of files in the root_dir that have an extension in `extensions`,
    excluding any files specified in the exclude_files list.

    Returns a string with file names and their contents.
    """
    if exclude_files is None:
        exclude_files = []
    file_contents = []
    for filename in os.listdir(root_dir):
        # Skip files in the exclusion list.
        if filename in exclude_files:
            continue
        filepath = os.path.join(root_dir, filename)
        # Only process files (not directories) with the specified extensions.
        if os.path.isfile(filepath) and any(filename.lower().endswith(ext) for ext in extensions):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"ERROR reading file: {e}"
            separator = "=" * 80
            file_contents.append(f"{separator}\nFilename: {filename}\n{separator}\n{content}\n")
    return "\n".join(file_contents)


def main():
    # Determine the root directory (folder where the script is run from)
    root_dir = os.getcwd()

    # Define the output file name.
    output_filename = "output.txt"

    # Generate the file tree for the entire directory structure.
    file_tree = generate_file_tree(root_dir)

    # Read the contents of .py, .csv, and .yaml files in the root folder only,
    # but exclude the output file.
    extensions = ['.py', '.csv', '.yaml']
    file_text = read_root_files(root_dir, extensions, exclude_files=[output_filename])

    # Combine both parts into one output.
    output = (
            "FILE TREE:\n"
            + file_tree +
            "\n\n" +
            "FILE CONTENTS (only root-level files with extensions: " + ", ".join(extensions) + "):\n\n" +
            file_text
    )

    # Write the combined output into 'output.txt'
    output_filepath = os.path.join(root_dir, output_filename)
    with open(output_filepath, "w", encoding="utf-8") as out_file:
        out_file.write(output)

    print(f"Report created: {output_filepath}")


if __name__ == '__main__':
    main()
