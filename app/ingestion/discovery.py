from pathlib import Path


EXTENSION_MAP = {
    ".md": "markdown",
    ".txt": "text",
    ".py": "python",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
}


SUPPORTED_EXTENSIONS = set(EXTENSION_MAP.keys())

def discover_files(source_dir: Path) -> list[Path]:
    """Return supported Files recursively from a source directory."""
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_dir}")

    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

def classify_file(path: Path) -> str:
    """Return the logical document type for a supported file."""
    extension = path.suffix.lower()
    
    if extension not in EXTENSION_MAP:
        raise ValueError(f"Unsupported file type: {extension}")
        
    return EXTENSION_MAP[extension]