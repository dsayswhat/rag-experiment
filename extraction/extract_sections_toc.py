#!/usr/bin/env python3
"""
Memory-efficient TOC-based PDF text extraction using PyMuPDF4LLM.
Uses PDF Table of Contents to determine section boundaries for reliable extraction.
Opens/closes PDF for each section to minimize memory usage.
Each TOC entry becomes a separate section, handling nested levels appropriately.
Optimized for PostgreSQL vector storage and LLM processing.
"""

import pymupdf4llm
import fitz  # For TOC and page counting
import json
import os
import sys
import argparse
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

def make_json_serializable(obj):
    """Convert PyMuPDF objects to JSON-serializable format"""
    if hasattr(obj, '__dict__'):
        return {k: make_json_serializable(v) for k, v in obj.__dict__.items()}
    elif hasattr(obj, 'x0') and hasattr(obj, 'y0'):
        return {
            'x0': getattr(obj, 'x0', 0),
            'y0': getattr(obj, 'y0', 0), 
            'x1': getattr(obj, 'x1', 0),
            'y1': getattr(obj, 'y1', 0)
        }
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)

def get_pdf_toc_and_pages(pdf_path: str) -> Tuple[List[Dict[str, Any]], int]:
    """Extract Table of Contents and total page count from PDF"""
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()
        page_count = len(doc)
        doc.close()
        
        # Convert TOC to more structured format
        toc_entries = []
        for level, title, page in toc:
            toc_entries.append({
                "level": level,
                "title": title.strip(),
                "page": page,
                "section_id": generate_section_id(title)
            })
        
        return toc_entries, page_count
    except Exception as e:
        print(f"Error reading PDF TOC: {e}")
        return [], 0

def generate_section_id(title: str) -> str:
    """Generate a clean section ID from title"""
    # Remove special characters and normalize
    section_id = re.sub(r'[^\w\s-]', '', title).strip()
    section_id = re.sub(r'\s+', '_', section_id).lower()
    # Ensure it starts with a letter (for database compatibility)
    if section_id and section_id[0].isdigit():
        section_id = f"section_{section_id}"
    return section_id or "untitled_section"

def calculate_section_boundaries(toc_entries: List[Dict[str, Any]], total_pages: int, page_offset: int = 0) -> List[Dict[str, Any]]:
    """Calculate start and end pages for each section based on TOC"""
    sections = []
    
    for i, entry in enumerate(toc_entries):
        section = entry.copy()
        
        # Apply page offset
        start_page = entry["page"] + page_offset
        
        # Calculate end page (up to next TOC entry or end of document)
        if i + 1 < len(toc_entries):
            end_page = toc_entries[i + 1]["page"] + page_offset - 1
        else:
            end_page = total_pages
        
        # Ensure valid page ranges
        start_page = max(1, min(start_page, total_pages))
        end_page = max(start_page, min(end_page, total_pages))
        
        section.update({
            "start_page": start_page,
            "end_page": end_page,
            "page_count": end_page - start_page + 1
        })
        
        sections.append(section)
    
    return sections

def extract_section_content(pdf_path: str, section: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract content for a single section using PyMuPDF4LLM.
    Opens and closes PDF for this section only to minimize memory usage.
    """
    start_page = section["start_page"]
    end_page = section["end_page"]
    
    print(f"  Extracting pages {start_page}-{end_page}...")
    
    try:
        # Extract pages for this section (PDF opened and closed within this call)
        pages_to_extract = list(range(start_page, end_page + 1))
        
        result = pymupdf4llm.to_markdown(
            pdf_path,
            pages=pages_to_extract,
            page_chunks=True,
            write_images=False
        )
        
        if not result:
            print(f"    Warning: No content extracted for section '{section['title']}'")
            return None
        
        # Combine all page content for this section
        combined_text = ""
        combined_metadata = {
            "pages": [],
            "total_chars": 0,
            "total_words": 0
        }
        
        for page_data in result:
            page_text = page_data.get('text', '')
            combined_text += page_text + "\n"
            
            # Collect page metadata
            page_info = {
                "page": page_data.get('page', 0),
                "chars": len(page_text),
                "words": len(page_text.split())
            }
            combined_metadata["pages"].append(page_info)
            combined_metadata["total_chars"] += page_info["chars"]
            combined_metadata["total_words"] += page_info["words"]
        
        # Create section content
        section_content = {
            "title": section["title"],
            "section_id": section["section_id"],
            "level": section["level"],
            "text": combined_text.strip(),
            "page_range": f"{start_page}-{end_page}",
            "start_page": start_page,
            "end_page": end_page,
            "page_count": section["page_count"],
            "character_count": combined_metadata["total_chars"],
            "word_count": combined_metadata["total_words"],
            "extraction_metadata": make_json_serializable(combined_metadata)
        }
        
        return section_content
        
    except Exception as e:
        print(f"    Error extracting section '{section['title']}': {e}")
        return None

def save_section_immediately(section: Dict[str, Any], output_dir: str, pdf_filename: str) -> str:
    """
    Save section to file immediately and return file path.
    This prevents accumulating sections in memory.
    """
    Path(output_dir).mkdir(exist_ok=True)
    
    # Create filename
    filename = f"{pdf_filename}_section_{section['section_id']}.md"
    filepath = Path(output_dir) / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {section['title']}\n\n")
        f.write(f"**Pages:** {section['start_page']}-{section['end_page']} ({section['page_count']} pages)\n")
        f.write(f"**Characters:** {section['character_count']}\n")
        f.write(f"**Words:** {section['word_count']}\n")
        f.write(f"**Section ID:** {section['section_id']}\n")
        f.write(f"**TOC Level:** {section['level']}\n\n")
        f.write("---\n\n")
        f.write(section['text'])
    
    return str(filepath)

def extract_sections_by_toc(
    pdf_path: str,
    output_dir: str = "output",
    page_offset: int = 0,
    toc_levels: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Extract PDF sections based on Table of Contents entries.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted sections
        page_offset: Offset to apply to TOC page numbers (+ moves forward, - moves back)
        toc_levels: List of TOC levels to extract (e.g., [1, 2] for levels 1 and 2 only)
    """
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Get TOC and page count
    toc_entries, total_pages = get_pdf_toc_and_pages(pdf_path)
    
    if not toc_entries:
        print("Error: No Table of Contents found in PDF")
        print("Consider using extract-sections.py (header-based) or extract-dolmenwood.py (page-based) instead")
        return {"error": "No TOC found", "sections_extracted": 0}
    
    print(f"Found {len(toc_entries)} TOC entries in {total_pages} pages")
    if page_offset != 0:
        print(f"Applying page offset: {page_offset:+d}")
    
    # Filter by TOC levels if specified
    if toc_levels:
        original_count = len(toc_entries)
        toc_entries = [entry for entry in toc_entries if entry["level"] in toc_levels]
        print(f"Filtered to {len(toc_entries)} entries (levels {toc_levels}) from {original_count} total")
    
    # Calculate section boundaries
    sections = calculate_section_boundaries(toc_entries, total_pages, page_offset)
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Extract each section using memory-efficient approach
    extracted_sections_metadata = []
    created_files = []
    pdf_filename = Path(pdf_path).stem
    
    print(f"\nExtracting {len(sections)} sections using memory-efficient approach...")
    
    for i, section in enumerate(sections, 1):
        print(f"\nSection {i}/{len(sections)}: {section['title']}")
        print(f"  Level {section['level']}, Pages {section['start_page']}-{section['end_page']}")
        
        # Extract section content (PDF opened and closed within this call)
        section_content = extract_section_content(pdf_path, section)
        
        if section_content:
            # Save section immediately to prevent memory accumulation
            section_file = save_section_immediately(section_content, output_dir, pdf_filename)
            created_files.append(section_file)
            
            # Store only metadata (not full content) to save memory
            section_metadata = {
                "title": section_content["title"],
                "id": section_content["section_id"], 
                "start_page": section_content["start_page"],
                "end_page": section_content["end_page"],
                "character_count": section_content["character_count"],
                "word_count": section_content["word_count"],
                "file_path": section_file,
                "toc_level": section_content["level"]
            }
            extracted_sections_metadata.append(section_metadata)
            
            print(f"    Saved: {Path(section_file).name} ({section_content['character_count']} chars)")
        else:
            print(f"    Skipped: No content extracted")
    
    # Create summary using only metadata (memory efficient)
    summary = {
        "pdf_file": Path(pdf_path).stem,
        "success": True,
        "extraction_method": "toc_based_memory_efficient",
        "total_pages": total_pages,
        "sections_found": len(extracted_sections_metadata),
        "page_offset_applied": page_offset,
        "toc_levels_filtered": toc_levels,
        "toc_entries_found": len(toc_entries),
        "created_files": created_files,
        "sections": extracted_sections_metadata
    }
    
    # Save summary
    summary_file = Path(output_dir) / f"{pdf_filename}_toc_sections_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\nExtraction complete!")
    print(f"- Sections found: {len(extracted_sections_metadata)}")
    print(f"- Files created: {len(created_files)}")
    print(f"- Summary saved: {summary_file}")
    print(f"- Output directory: {output_dir}")
    
    return summary

def main():
    """Main CLI interface for TOC-based PDF extraction."""
    parser = argparse.ArgumentParser(
        description="Extract PDF sections using Table of Contents entries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all TOC entries
  python extract_sections_toc.py book.pdf
  
  # Extract with page offset (if TOC page numbers are off by 2)
  python extract_sections_toc.py book.pdf --page-offset -2
  
  # Extract only main chapters (level 1 TOC entries)
  python extract_sections_toc.py book.pdf --toc-levels 1
  
  # Extract chapters and sections (levels 1 and 2)
  python extract_sections_toc.py book.pdf --toc-levels 1 2
  
  # Custom output directory
  python extract_sections_toc.py book.pdf --output-dir extracted_content
        """
    )
    
    parser.add_argument('pdf_file', help='PDF file to extract sections from')
    parser.add_argument('--output-dir', default='output', 
                       help='Output directory for extracted sections (default: output)')
    parser.add_argument('--page-offset', type=int, default=0,
                       help='Offset to apply to TOC page numbers (+ forward, - backward)')
    parser.add_argument('--toc-levels', type=int, nargs='+',
                       help='Extract only specified TOC levels (e.g., --toc-levels 1 2)')
    
    args = parser.parse_args()
    
    try:
        summary = extract_sections_by_toc(
            args.pdf_file,
            args.output_dir,
            args.page_offset,
            args.toc_levels
        )
        
        if "error" in summary:
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()