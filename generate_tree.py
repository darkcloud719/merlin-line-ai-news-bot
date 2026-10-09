from pathlib import Path

IGNORED_NAMES = {".venv", ".git", "__pycache__", ".pytest_cache", "tree.txt"}

def generate_tree(path: Path, prefix: str = "") -> list[str]:
    """Recursively generates a tree structure of the given directory."""
    lines = []
    entries = sorted(
        (entry for entry in path.iterdir() if entry.name not in IGNORED_NAMES),
        key=lambda entry: (entry.is_file(), entry.name.lower()),
    )

    for i, entry in enumerate(entries):
        connector = "├── " if i < len(entries) - 1 else "└── "
        lines.append(f"{prefix}{connector}{entry.name}")

        if entry.is_dir():
            extension = "│   " if i < len(entries) - 1 else "    "
            lines.extend(generate_tree(entry, prefix + extension))

    return lines

def main() -> None:
    root = Path.cwd()
    tree_lines = generate_tree(root)
    (root / "tree.txt").write_text("\n".join(tree_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
