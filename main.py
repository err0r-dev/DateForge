#!/usr/bin/env python3
"""
DateForge - Intelligent PDF date extraction and renaming tool
Processes PDFs in parallel, extracts dates from document content, and renames files with YYYYMMDD prefix.
"""

from __future__ import annotations

import io
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pdfplumber
from dateutil import parser as date_parser
from tqdm import tqdm

# Configuration constants
EIGHT_DIGIT_PREFIX = re.compile(r"^\d{8}_.+\.pdf$", re.IGNORECASE)
MIN_YEAR = 1900
MAX_YEAR = 2100
MAX_TEXT_SCAN_PAGES = 3  # Only scan first 3 pages for text
MAX_OCR_PAGES = 2  # Only OCR first 2 pages if needed
MIN_TEXT_THRESHOLD = 50  # Minimum characters to consider text extraction successful
OCR_ZOOM = 1.5  # Reduced from 2.78x for faster OCR

# Common date patterns (ordered by likelihood)
# These patterns capture various date formats found in documents
DATE_PATTERNS = [
    # Numeric formats
    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # DD/MM/YYYY or MM/DD/YYYY
    r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY-MM-DD
    r'\b\d{1,2}\.\d{1,2}\.\d{4}\b',  # DD.MM.YYYY

    # Ordinal dates with full month names: "3rd September 2025", "21st January 2025"
    r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b',

    # Month-first formats: "September 3rd 2025", "January 21st, 2025"
    r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',

    # Simple formats without ordinals: "3 Sep 2025", "21 January 2025"
    r'\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b',

    # Month-first simple: "Sep 3 2025", "January 21, 2025"
    r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b',
]
COMPILED_DATE_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in DATE_PATTERNS]


class ProcessingStats:
    """Track processing statistics"""
    def __init__(self):
        self.total = 0
        self.skipped = 0
        self.renamed = 0
        self.no_date = 0
        self.errors = 0
        self.start_time = time.time()

    def print_summary(self):
        elapsed = time.time() - self.start_time
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Total PDFs found:        {self.total}")
        print(f"Already formatted:       {self.skipped}")
        print(f"Successfully renamed:    {self.renamed}")
        print(f"No date found:           {self.no_date}")
        print(f"Errors:                  {self.errors}")
        print(f"Processing time:         {elapsed:.2f}s")
        if elapsed > 0:
            print(f"Speed:                   {self.total / elapsed:.2f} files/sec")
        print("="*60)


def main() -> None:
    """Main entry point"""
    folder = prompt_for_folder()

    # Separate PDF and non-PDF files
    all_files = sorted(p for p in folder.iterdir() if p.is_file())
    pdf_files = [p for p in all_files if p.suffix.lower() == ".pdf"]
    non_pdf_files = [p for p in all_files if p.suffix.lower() != ".pdf"]

    # Handle non-PDF files first
    if non_pdf_files:
        not_pdf_dir = folder / "* Not a PDF"
        not_pdf_dir.mkdir(exist_ok=True)
        print(f"\nMoving {len(non_pdf_files)} non-PDF files to '* Not a PDF' folder...")
        for file_path in non_pdf_files:
            target = ensure_unique_name(not_pdf_dir / file_path.name)
            file_path.replace(target)
            print(f"  Moved: {file_path.name}")

    if not pdf_files:
        print(f"\nNo PDFs found in {folder}")
        return

    stats = ProcessingStats()
    stats.total = len(pdf_files)

    # Filter out already-formatted files
    files_to_process = []
    for pdf_path in pdf_files:
        if EIGHT_DIGIT_PREFIX.match(pdf_path.name):
            stats.skipped += 1
            print(f"Skipping (already formatted): {pdf_path.name}")
        else:
            files_to_process.append(pdf_path)

    if not files_to_process:
        print("\nAll PDFs already have date prefix!")
        stats.print_summary()
        return

    print(f"\nProcessing {len(files_to_process)} PDFs using parallel workers...")

    no_date_dir: Optional[Path] = None

    # Process PDFs in parallel
    max_workers = min(8, len(files_to_process))
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {
            executor.submit(process_single_pdf, pdf_path): pdf_path
            for pdf_path in files_to_process
        }

        # Process results as they complete
        with tqdm(total=len(files_to_process), desc="Processing PDFs", unit="file") as progress:
            for future in as_completed(future_to_path):
                pdf_path = future_to_path[future]
                progress.set_postfix_str(pdf_path.name[:40])

                try:
                    result = future.result()

                    if result['status'] == 'error':
                        stats.errors += 1
                        tqdm.write(f"ERROR: {pdf_path.name}: {result['message']}")

                    elif result['status'] == 'renamed':
                        stats.renamed += 1
                        # Perform the actual rename in the main process
                        date_value = datetime.fromisoformat(result['date'])
                        new_name = build_new_filename(pdf_path, date_value)
                        target_path = ensure_unique_name(pdf_path.with_name(new_name))
                        pdf_path.replace(target_path)
                        tqdm.write(f"RENAMED: {pdf_path.name} -> {target_path.name}")

                    elif result['status'] == 'no_date':
                        stats.no_date += 1
                        # Move to "* No Date Found" folder
                        if no_date_dir is None:
                            no_date_dir = folder / "* No Date Found"
                            no_date_dir.mkdir(exist_ok=True)

                        target = ensure_unique_name(no_date_dir / pdf_path.name)
                        pdf_path.replace(target)
                        tqdm.write(f"NO DATE: {pdf_path.name} -> * No Date Found/")

                except Exception as exc:
                    stats.errors += 1
                    tqdm.write(f"EXCEPTION: {pdf_path.name}: {exc}")

                progress.update(1)

    stats.print_summary()


def process_single_pdf(pdf_path: Path) -> dict:
    """
    Process a single PDF file (runs in worker process).
    Returns a dict with status and metadata.
    """
    try:
        date_value = scan_pdf_for_date(pdf_path)

        if date_value is None:
            return {'status': 'no_date', 'path': str(pdf_path)}

        return {
            'status': 'renamed',
            'path': str(pdf_path),
            'date': date_value.isoformat()
        }

    except Exception as exc:
        return {
            'status': 'error',
            'path': str(pdf_path),
            'message': str(exc)
        }


def scan_pdf_for_date(pdf_path: Path) -> Optional[datetime]:
    """
    Scan PDF for date using multiple strategies:
    1. PyMuPDF text extraction (fast, works for most PDFs)
    2. pdfplumber text extraction (better for complex layouts)
    3. OCR fallback (slow, only if text extraction fails)
    """
    # Strategy 1: PyMuPDF text extraction (fastest)
    date_value = extract_date_with_pymupdf(pdf_path)
    if date_value:
        return date_value

    # Strategy 2: pdfplumber (better text extraction)
    date_value = extract_date_with_pdfplumber(pdf_path)
    if date_value:
        return date_value

    # Strategy 3: OCR fallback (slowest, only if needed)
    date_value = extract_date_with_ocr(pdf_path)
    if date_value:
        return date_value

    return None


def extract_date_with_pymupdf(pdf_path: Path) -> Optional[datetime]:
    """Extract date using PyMuPDF (fast but may miss some text)"""
    try:
        with fitz.open(pdf_path) as doc:
            pages_to_scan = min(MAX_TEXT_SCAN_PAGES, doc.page_count)

            for page_num in range(pages_to_scan):
                page = doc.load_page(page_num)
                text = page.get_text("text")

                if len(text) >= MIN_TEXT_THRESHOLD:
                    date_value = extract_date_from_text(text)
                    if date_value:
                        return date_value
    except Exception:
        pass  # Fall through to next strategy

    return None


def extract_date_with_pdfplumber(pdf_path: Path) -> Optional[datetime]:
    """Extract date using pdfplumber (better text extraction)"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_scan = min(MAX_TEXT_SCAN_PAGES, len(pdf.pages))

            for page_num in range(pages_to_scan):
                text = pdf.pages[page_num].extract_text()

                if text and len(text) >= MIN_TEXT_THRESHOLD:
                    date_value = extract_date_from_text(text)
                    if date_value:
                        return date_value
    except Exception:
        pass  # Fall through to next strategy

    return None


def extract_date_with_ocr(pdf_path: Path) -> Optional[datetime]:
    """Extract date using OCR (slowest, only as last resort)"""
    try:
        # Lazy import to avoid loading if not needed
        import numpy as np
        from easyocr import Reader
        from PIL import Image
    except ImportError:
        # OCR dependencies not installed
        return None

    try:
        # Initialize OCR reader (cached globally in worker process)
        reader = Reader(["en"], gpu=False)  # Disable GPU for stability

        with fitz.open(pdf_path) as doc:
            pages_to_scan = min(MAX_OCR_PAGES, doc.page_count)

            for page_num in range(pages_to_scan):
                page = doc.load_page(page_num)

                # Render at lower resolution for speed
                matrix = fitz.Matrix(OCR_ZOOM, OCR_ZOOM)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)

                # Convert to image and run OCR
                with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
                    text_chunks = reader.readtext(np.array(image), detail=0, paragraph=True)
                    text = "\n".join(text_chunks) if text_chunks else ""

                    if text:
                        date_value = extract_date_from_text(text)
                        if date_value:
                            return date_value
    except Exception:
        pass

    return None


def extract_date_from_text(text: str) -> Optional[datetime]:
    """
    Extract date from text using fast regex + dateutil parser.
    Looks for common date patterns first, then tries parsing.
    """
    if not text:
        return None

    # Try regex patterns first (fast)
    date_candidates = []
    for pattern in COMPILED_DATE_PATTERNS:
        matches = pattern.findall(text)
        date_candidates.extend(matches)

    # Parse each candidate
    valid_dates = []
    for candidate in date_candidates:
        try:
            # Use dateutil parser with dayfirst=True for DD/MM/YYYY preference
            parsed = date_parser.parse(candidate, dayfirst=True, fuzzy=False)

            # Validate year range
            if MIN_YEAR <= parsed.year <= MAX_YEAR:
                valid_dates.append(parsed)
        except (ValueError, OverflowError):
            continue

    # Return earliest valid date
    if valid_dates:
        return min(valid_dates)

    return None


def prompt_for_folder() -> Path:
    """Prompt user for folder path"""
    while True:
        user_input = input("Enter the folder path containing PDFs: ").strip()

        # Remove quotes if present
        if len(user_input) >= 2 and user_input[0] == user_input[-1] and user_input[0] in {"'", '"'}:
            user_input = user_input[1:-1]

        target = Path(user_input).expanduser()

        if target.exists() and target.is_dir():
            return target

        print(f"Folder '{target}' does not exist or is not a directory. Please try again.")


def build_new_filename(original: Path, date_value: datetime) -> str:
    """Build new filename with YYYYMMDD prefix"""
    return f"{date_value:%Y%m%d}_{original.stem}.pdf"


def ensure_unique_name(target: Path) -> Path:
    """Ensure filename is unique by appending counter if needed"""
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
