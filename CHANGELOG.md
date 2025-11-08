# Changelog

All notable changes to DateForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-08

### Initial Release

DateForge v1.0.0 is an intelligent PDF date extraction and renaming tool that automatically organizes your PDF documents by extracting dates and prefixing filenames with YYYYMMDD format.

### Features

#### Core Functionality
- **Automatic Date Detection**: Extracts dates from PDF content using multiple strategies
- **Smart Filename Prefix**: Renames PDFs with YYYYMMDD_ prefix for easy sorting
- **Parallel Processing**: Processes multiple PDFs simultaneously for maximum speed
- **Intelligent Organization**: Automatically organizes files into categorized folders

#### Date Format Support
Recognizes all common date formats:
- Numeric: `03/09/2025`, `2025-09-03`, `3.9.2025`
- Text with ordinals: `3rd September 2025`, `21st January 2025`
- Month-first: `September 3rd, 2025`, `Sep 3 2025`
- Simple text: `3 Sep 2025`, `21 January 2025`
- Full and abbreviated month names
- Case-insensitive matching

#### Multi-Tier Text Extraction
1. **PyMuPDF extraction** (fastest, works for most PDFs)
2. **pdfplumber extraction** (better for complex layouts)
3. **OCR fallback** (optional, for scanned documents)

#### File Organization
- **`* No Date Found/`**: PDFs where no date could be extracted
- **`* Not a PDF/`**: Non-PDF files found in the folder
- Asterisk prefix ensures these folders appear at the top

#### Performance Optimizations
- Parallel processing using up to 8 worker processes
- Smart page scanning (first 3 pages for text, 2 for OCR)
- Pre-compiled regex patterns for fast date matching
- Lightweight dependencies for quick installation

#### User Experience
- Real-time progress bar with file tracking
- Detailed processing summary with statistics
- Clear status messages (RENAMED, NO DATE, ERROR)
- Processing speed metrics (files/sec)
- Automatic handling of duplicate filenames

### Technical Details

#### Dependencies
**Core (required):**
- `pymupdf` - Fast PDF parsing
- `pdfplumber` - Enhanced text extraction
- `python-dateutil` - Flexible date parsing
- `tqdm` - Progress visualization

**Optional (OCR support):**
- `easyocr` - Optical character recognition
- `numpy` - Array operations for OCR
- `pillow` - Image processing

#### Requirements
- Python 3.13 or higher
- UV package manager

#### Installation Size
- Core installation: ~500MB
- With OCR support: ~2-3GB

### Usage

```bash
# Install dependencies and run
./run.sh

# Or manually
uv sync
uv run python main.py
```

### License

Licensed under [Err0r.dev Open Use License](https://github.com/err0r-dev/.github/blob/main/profile/license.md)

[1.0.0]: https://github.com/yourusername/dateforge/releases/tag/v1.0.0
