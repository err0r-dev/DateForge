# DateForge

> Intelligent PDF date extraction and renaming tool

DateForge automatically extracts dates from your PDF documents and renames them with a `YYYYMMDD_` prefix for perfect chronological sorting. Process hundreds of PDFs in seconds with parallel processing and smart text extraction.

## Features

### Automatic Date Detection
- Extracts dates from PDF content using intelligent multi-tier strategy
- Supports all common date formats (numeric, text, ordinals)
- Handles both digital and scanned PDFs

### Lightning Fast Processing
- Parallel processing using up to 8 worker processes
- Processes 30+ files per second on modern hardware
- Smart optimization: only scans necessary pages

### Intelligent Organization
- Renames PDFs with `YYYYMMDD_` prefix for chronological sorting
- Moves undated PDFs to `* No Date Found/` folder
- Moves non-PDF files to `* Not a PDF/` folder
- Asterisk prefix keeps special folders at the top

### Comprehensive Date Format Support

DateForge recognizes all these formats and more:

```
03/09/2025          → September 3, 2025
2025-09-03          → September 3, 2025
3.9.2025            → September 3, 2025
3rd September 2025  → September 3, 2025
September 3rd, 2025 → September 3, 2025
3 Sep 2025          → September 3, 2025
21st January 2025   → January 21, 2025
Jan 21, 2025        → January 21, 2025
```

Supports:
- Full month names (September, January) and abbreviations (Sep, Jan)
- Ordinal suffixes (st, nd, rd, th)
- Multiple date separators (/, -, .)
- Case-insensitive matching

## Installation

### Prerequisites

1. **Python 3.13 or higher**
2. **UV package manager** - [Install UV](https://github.com/astral-sh/uv)

```bash
# Quick UV installation
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install DateForge

```bash
# Clone the repository
git clone https://github.com/yourusername/dateforge.git
cd dateforge

# Install dependencies
uv sync

# Optional: Install OCR support for scanned PDFs
uv sync --extra ocr
```

## Usage

### Quick Start

```bash
# Run the script
./run.sh
```

Or manually:

```bash
uv run python main.py
```

### Example Workflow

1. **Run the script**: `./run.sh`
2. **Enter folder path**: `/path/to/your/pdfs`
3. **Watch the magic**: DateForge processes files in parallel
4. **Review results**: Check the summary statistics

### Example Output

```
Processing 75 PDFs using parallel workers...

RENAMED: Invoice_Sept.pdf -> 20250903_Invoice_Sept.pdf
RENAMED: Receipt.pdf -> 20250815_Receipt.pdf
NO DATE: Brochure.pdf -> * No Date Found/

============================================================
PROCESSING SUMMARY
============================================================
Total PDFs found:        82
Already formatted:       7
Successfully renamed:    43
No date found:           32
Errors:                  0
Processing time:         2.20s
Speed:                   37.25 files/sec
============================================================
```

## How It Works

### Multi-Tier Date Extraction Strategy

DateForge uses a sophisticated three-tier approach:

1. **Tier 1: PyMuPDF Text Extraction** (fastest)
   - Extracts text directly from PDF structure
   - Works for 90%+ of digital PDFs
   - Scans first 3 pages

2. **Tier 2: pdfplumber Extraction** (better accuracy)
   - Enhanced text extraction for complex layouts
   - Handles tables and multi-column documents
   - Fallback if Tier 1 finds insufficient text

3. **Tier 3: OCR Fallback** (optional, for scanned PDFs)
   - Optical character recognition for image-based PDFs
   - Only activates if text extraction fails
   - Requires optional OCR dependencies

### Date Pattern Matching

- Uses pre-compiled regex patterns for speed
- Leverages `python-dateutil` for flexible parsing
- Validates dates within 1900-2100 range
- Selects earliest valid date if multiple found

### File Organization

```
Your Folder/
├── 20250903_Invoice.pdf          ← Renamed with date
├── 20250815_Receipt.pdf          ← Renamed with date
├── * No Date Found/              ← Undated PDFs
│   ├── Brochure.pdf
│   └── Flyer.pdf
└── * Not a PDF/                  ← Non-PDF files
    ├── document.docx
    └── image.jpg
```

## Configuration

### Constants (in main.py)

```python
MAX_TEXT_SCAN_PAGES = 3   # Pages to scan for text
MAX_OCR_PAGES = 2         # Pages to OCR if needed
MIN_TEXT_THRESHOLD = 50   # Min chars for valid text
OCR_ZOOM = 1.5            # OCR resolution multiplier
MIN_YEAR = 1900           # Earliest valid year
MAX_YEAR = 2100           # Latest valid year
```

## Performance

### Benchmarks

Tested on MacBook Pro M1 with 75 PDFs:

- **Processing Time**: 2.20 seconds
- **Speed**: 37.25 files/second
- **Success Rate**: 57% dates found
- **Worker Processes**: 8 parallel workers

### Tips for Maximum Speed

1. **SSD Storage**: Store PDFs on SSD for faster I/O
2. **Skip OCR**: Don't install OCR dependencies if not needed
3. **Batch Processing**: Process large folders at once
4. **Modern CPU**: More cores = more parallel processing

## Dependencies

### Core Dependencies (Required)

| Package | Purpose | Size |
|---------|---------|------|
| `pymupdf` | Fast PDF parsing | ~50MB |
| `pdfplumber` | Enhanced text extraction | ~20MB |
| `python-dateutil` | Flexible date parsing | ~300KB |
| `tqdm` | Progress bars | ~100KB |

**Total Core Size**: ~500MB

### Optional Dependencies (OCR Support)

| Package | Purpose | Size |
|---------|---------|------|
| `easyocr` | Optical character recognition | ~100MB |
| `numpy` | Array operations | ~50MB |
| `pillow` | Image processing | ~10MB |
| PyTorch (via easyocr) | Neural networks | ~500MB+ |

**Total with OCR**: ~2-3GB

## Troubleshooting

### Common Issues

#### "UV is required"
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### "No module named 'fitz'"
```bash
# Reinstall dependencies
uv sync --reinstall
```

#### OCR not working
```bash
# Install optional OCR dependencies
uv sync --extra ocr
```

#### "Permission denied: ./run.sh"
```bash
# Make script executable
chmod +x run.sh
```

### Getting Help

- Check [Issues](https://github.com/yourusername/dateforge/issues) for known problems
- Search [Discussions](https://github.com/yourusername/dateforge/discussions) for community help
- Review the [CHANGELOG](CHANGELOG.md) for version-specific notes

## Development

### Project Structure

```
dateforge/
├── main.py              # Main application logic
├── run.sh              # Launcher script
├── pyproject.toml      # Project configuration
├── README.md           # This file
├── CHANGELOG.md        # Version history
└── .dateforge-venv/    # Virtual environment (created on first run)
```

### Key Functions

- `scan_pdf_for_date()` - Multi-tier date extraction
- `extract_date_with_pymupdf()` - Fast text extraction
- `extract_date_with_pdfplumber()` - Enhanced extraction
- `extract_date_with_ocr()` - OCR fallback
- `extract_date_from_text()` - Pattern matching and parsing

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Licensed under [Err0r.dev Open Use License](https://github.com/err0r-dev/.github/blob/main/profile/license.md)

## Acknowledgments

- Built with [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF processing
- Uses [pdfplumber](https://github.com/jsvine/pdfplumber) for enhanced text extraction
- Powered by [python-dateutil](https://github.com/dateutil/dateutil) for flexible date parsing
- Optional OCR via [EasyOCR](https://github.com/JaidedAI/EasyOCR)

## Version

Current version: **1.0.0**

See [CHANGELOG.md](CHANGELOG.md) for version history.
