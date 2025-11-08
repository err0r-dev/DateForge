from __future__ import annotations

import importlib
import io
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

REQUIRED_MODULES = {
    "fitz": "pymupdf",
    "dateparser": "dateparser",
    "easyocr": "easyocr",
    "numpy": "numpy",
    "PIL": "pillow",
}


def ensure_dependencies() -> None:
    missing: list[str] = []
    for module_name, package_name in REQUIRED_MODULES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)

    if not missing:
        return

    uv_path = shutil.which("uv")
    if uv_path is None:
        raise RuntimeError(
            "UV is required to install dependencies automatically. Install UV and rerun the script."
        )

    print(f"Installing missing dependencies via UV: {', '.join(missing)}")
    result = subprocess.run([uv_path, "pip", "install", *missing])
    if result.returncode != 0:
        raise RuntimeError("Failed to install dependencies with UV. Please install them manually.")


ensure_dependencies()

import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from dateparser.search import search_dates

if TYPE_CHECKING:
    from easyocr import Reader

EIGHT_DIGIT_PREFIX = re.compile(r"^\d{8}_.+\.pdf$", re.IGNORECASE)
MIN_YEAR = 1900
MAX_YEAR = 2100
OCR_READER: "Reader | None" = None

try:
    import easyocr
except ImportError:  # pragma: no cover - dependency is declared via uv
    easyocr = None  # type: ignore[assignment]


def main() -> None:
    folder = prompt_for_folder()
    pdf_files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]

    if not pdf_files:
        print(f"No PDFs found in {folder}")
        return

    no_date_dir: Optional[Path] = None

    for pdf_path in sorted(pdf_files):
        if EIGHT_DIGIT_PREFIX.match(pdf_path.name):
            print(f"Skipping (already formatted): {pdf_path.name}")
            continue

        try:
            new_path = handle_pdf(pdf_path)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Failed to process {pdf_path.name}: {exc}")
            continue

        if new_path is None:
            if no_date_dir is None:
                no_date_dir = folder / "No Date Found"
                no_date_dir.mkdir(exist_ok=True)

            target = ensure_unique_name(no_date_dir / pdf_path.name)
            pdf_path.replace(target)
            print(f"Moved to 'No Date Found': {target.relative_to(folder)}")
        else:
            print(f"Renamed to: {new_path.name}")


def prompt_for_folder() -> Path:
    while True:
        user_input = input("Enter the folder path containing PDFs: ").strip()
        target = Path(user_input).expanduser()
        if target.exists() and target.is_dir():
            return target
        print(f"Folder '{target}' does not exist or is not a directory. Please try again.")


def handle_pdf(pdf_path: Path) -> Optional[Path]:
    """Return new path when renamed, otherwise None if no date found."""
    with fitz.open(pdf_path) as document:
        text = "\n".join(
            document.load_page(index).get_text("text") for index in range(document.page_count)
        )
        date_value = extract_date(text)

        if date_value is None:
            ocr_text = extract_text_via_ocr(document)
            date_value = extract_date(ocr_text)

    if date_value is None:
        return None

    new_name = build_new_filename(pdf_path, date_value)
    target_path = ensure_unique_name(pdf_path.with_name(new_name))
    pdf_path.replace(target_path)
    return target_path


def extract_date(text: str) -> Optional[datetime]:
    if not text:
        return None

    results = search_dates(
        text,
        settings={
            "DATE_ORDER": "DMY",
            "PREFER_DAY_OF_MONTH": "first",
            "REQUIRE_PARTS": ["day", "month", "year"],
        },
    )

    if not results:
        return None

    candidates = [
        result.date()
        for _, result in results
        if MIN_YEAR <= result.year <= MAX_YEAR
    ]

    if not candidates:
        return None

    chosen = min(candidates)
    return datetime.combine(chosen, datetime.min.time())


def extract_text_via_ocr(document: fitz.Document) -> str:
    reader = get_ocr_reader()
    if reader is None:
        return ""

    aggregated: list[str] = []
    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        pixmap = render_page_as_pixmap(page)
        if pixmap is None:
            continue

        with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
            text_chunks = reader.readtext(np.array(image), detail=0, paragraph=True)
            if text_chunks:
                aggregated.append("\n".join(text_chunks))

    return "\n".join(aggregated)


def render_page_as_pixmap(page: fitz.Page) -> Optional[fitz.Pixmap]:
    try:
        zoom = 200 / 72  # upscale for better OCR accuracy
        matrix = fitz.Matrix(zoom, zoom)
        return page.get_pixmap(matrix=matrix, alpha=False)
    except RuntimeError:
        return None


def get_ocr_reader() -> Optional["Reader"]:
    global OCR_READER
    if easyocr is None:
        return None
    if OCR_READER is None:
        OCR_READER = easyocr.Reader(["en"], gpu=False)
    return OCR_READER


def build_new_filename(original: Path, date_value: datetime) -> str:
    return f"{date_value:%Y%m%d}_{original.stem}.pdf"


def ensure_unique_name(target: Path) -> Path:
    if not target.exists():
        return target

    counter = 1
    stem = target.stem
    suffix = target.suffix or ".pdf"

    while True:
        candidate = target.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


if __name__ == "__main__":
    main()
