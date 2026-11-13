"""Rebuild downloads/GFlow-browser-extension.zip from browser-extension/."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "browser-extension"
ARCHIVE = ROOT / "downloads/GFlow-browser-extension.zip"
TEXT_SUFFIXES = {".js", ".json", ".html", ".css", ".md"}


def extension_files():
    """Archive name to bytes, with text line endings normalized so every OS packs the same archive."""
    files = {}
    for path in sorted(SOURCE.iterdir(), key=lambda item: item.name):
        if path.is_file():
            data = path.read_bytes()
            files[path.name] = data.replace(b"\r\n", b"\n") if path.suffix in TEXT_SUFFIXES else data
    return files


def main():
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in extension_files().items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    print(f"wrote {ARCHIVE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
