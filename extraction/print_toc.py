#!/usr/bin/env python3
"""
Opens a PDF and pretty-prints the Table of Contents.
"""

import fitz  # PyMuPDF
import argparse
from pathlib import Path

def print_pretty_toc(pdf_path: str):
    """Extracts and prints the Table of Contents from a PDF."""
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"Table of Contents for: {Path(pdf_path).name}")
    print("="*60)

    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()
        doc.close()

        if not toc:
            print("No Table of Contents found in this PDF.")
            return

        for level, title, page in toc:
            indent = "  " * (level - 1)
            print(f"{indent}{title} (p. {page})")

    except Exception as e:
        print(f"An error occurred while reading the PDF: {e}")

def main():
    """Main CLI interface for printing the ToC."""
    parser = argparse.ArgumentParser(
        description="Pretty-print the Table of Contents of a PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python print_toc.py path/to/book.pdf
        """
    )
    parser.add_argument('pdf_file', help='PDF file to analyze')

    args = parser.parse_args()

    try:
        print_pretty_toc(args.pdf_file)
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
