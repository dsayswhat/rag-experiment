#!/usr/bin/env python3
"""
Memory-efficient section-based PDF text extraction using PyMuPDF4LLM.
Opens/closes PDF for each section to minimize memory usage.
Groups pages by section headers (##### Title) for semantic content chunks.
Optimized for PostgreSQL vector storage and LLM processing.
"""

import pymupdf4llm
import fitz  # For page counting
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

def get_pdf_page_count(pdf_path: str) -> int:
    """Get total page count from PDF without loading content"""
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        return page_count
    except Exception as e:
        print(f"Error reading PDF page count: {e}")
        return 0

def find_section_header_in_text(text: str) -> Optional[Tuple[str, int]]:
    """
    Find the first section header in markdown text.
    
    Returns:
        (header_title, line_number) or None if no header found
    """
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        # Look for 5-level headers (##### Title)
        match = re.match(r'^#{5}\s+(.+)$', line.strip())
        if match:
            header_title = match.group(1).strip()
            return (header_title, i)
    
    return None

def extract_next_section(
    pdf_path: str, 
    start_page: int, 
    total_pages: int,
    look_ahead_pages: int = 20
) -> Tuple[Optional[Dict[str, Any]], int]:
    """
    Extract the next section starting from start_page.
    Opens PDF, finds section boundary, extracts content, closes PDF.
    
    Args:
        pdf_path: Path to PDF file
        start_page: Page to start extraction from
        total_pages: Total pages in PDF
        look_ahead_pages: How many pages to scan ahead for next header
        
    Returns:
        (section_data, next_start_page) tuple
        section_data is None if no more sections found
    """
    
    if start_page > total_pages:
        return None, start_page
    
    # Determine page range to extract
    # Start with a reasonable batch, but we'll expand if needed
    initial_batch_size = min(look_ahead_pages, total_pages - start_page + 1)
    pages_to_extract = list(range(start_page, start_page + initial_batch_size))
    
    try:
        print(f"  Scanning pages {start_page}-{start_page + initial_batch_size - 1} for section boundaries...")
        
        # Extract initial batch to find section boundaries
        result = pymupdf4llm.to_markdown(
            pdf_path,
            pages=pages_to_extract,
            page_chunks=True,
            write_images=False
        )
        
        if not result:
            return None, start_page + 1
        
        # Analyze content to find section boundaries
        first_page_data = result[0]
        first_page_text = first_page_data.get('text', '')
        first_header = find_section_header_in_text(first_page_text)
        
        if not first_header:
            # No header on first page - this might be continuation of previous section
            # or we're starting mid-document. Create a section anyway.
            section_title = f"Content starting at Page {start_page}"
            section_id = f"untitled_page_{start_page}"
            header_title = section_title
        else:
            header_title, _ = first_header
            section_id = re.sub(r'[^\w\s-]', '', header_title).strip()
            section_id = re.sub(r'\s+', '_', section_id).lower()
        
        # Look for next section header in subsequent pages
        section_end_page = start_page + len(result) - 1  # Default to end of batch
        next_section_start = None
        
        for i, page_data in enumerate(result[1:], 1):  # Skip first page
            page_text = page_data.get('text', '')
            header = find_section_header_in_text(page_text)
            
            if header:
                # Found next section header
                section_end_page = start_page + i - 1  # End current section before this page
                next_section_start = start_page + i
                print(f"    Next section found at page {next_section_start}: '{header[0]}'")
                break
        
        # If no next header found and we haven't reached end of document,
        # we might need to look further ahead
        if next_section_start is None and section_end_page == start_page + initial_batch_size - 1 and section_end_page < total_pages:
            # Extend search for next header
            extended_pages = list(range(section_end_page + 1, min(total_pages + 1, section_end_page + 21)))
            
            if extended_pages:
                print(f"    Extending search to pages {extended_pages[0]}-{extended_pages[-1]}...")
                try:
                    extended_result = pymupdf4llm.to_markdown(
                        pdf_path,
                        pages=extended_pages,
                        page_chunks=True,
                        write_images=False
                    )
                    
                    for i, page_data in enumerate(extended_result):
                        page_text = page_data.get('text', '')
                        header = find_section_header_in_text(page_text)
                        
                        if header:
                            next_section_start = extended_pages[i]
                            print(f"    Next section found at page {next_section_start}: '{header[0]}'")
                            break
                        else:
                            section_end_page = extended_pages[i]  # Extend current section
                
                except Exception as e:
                    print(f"    Warning: Error extending search: {e}")
        
        # If still no next section found, this section goes to end of document
        if next_section_start is None:
            section_end_page = total_pages
            next_section_start = total_pages + 1
        
        # Now extract the complete section content
        print(f"    Extracting section: '{header_title}' (pages {start_page}-{section_end_page})")
        
        final_pages = list(range(start_page, section_end_page + 1))
        final_result = pymupdf4llm.to_markdown(
            pdf_path,
            pages=final_pages,
            page_chunks=True,
            write_images=False
        )
        
        # Combine all pages in section
        section_content = ""
        for page_data in final_result:
            page_text = page_data.get('text', '')
            if section_content:
                section_content += "\n\n" + page_text
            else:
                section_content = page_text
        
        section_info = {
            'section_id': section_id,
            'section_title': header_title,
            'start_page': start_page,
            'end_page': section_end_page,
            'pages': final_pages,
            'content': section_content,
            'character_count': len(section_content),
            'word_count': len(section_content.split()),
            'metadata': {
                'header_found': first_header is not None,
                'pages_in_section': len(final_pages),
                'extraction_method': 'memory_efficient'
            }
        }
        
        return section_info, next_section_start
        
    except Exception as e:
        print(f"    Error extracting section starting at page {start_page}: {e}")
        return None, start_page + 1

def save_section_immediately(section: Dict[str, Any], output_dir: str, base_filename: str) -> str:
    """
    Save section to file immediately and return file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean filename
    safe_filename = re.sub(r'[^\w\s-]', '', section['section_id'])
    safe_filename = re.sub(r'\s+', '_', safe_filename)
    section_file = os.path.join(output_dir, f"{base_filename}_section_{safe_filename}.md")
    
    with open(section_file, 'w', encoding='utf-8') as f:
        f.write(f"# {section['section_title']}\n\n")
        f.write(f"**Pages:** {section['start_page']}-{section['end_page']} ({len(section['pages'])} pages)\n")
        f.write(f"**Characters:** {section['character_count']}\n")
        f.write(f"**Words:** {section['word_count']}\n")
        f.write(f"**Section ID:** {section['section_id']}\n\n")
        f.write("---\n\n")
        f.write(section['content'])
    
    return section_file

def extract_all_sections(
    pdf_path: str,
    start_page: int = 1,
    output_dir: str = "output"
) -> Dict[str, Any]:
    """
    Extract all sections from PDF using memory-efficient approach.
    Each section is processed independently with PDF open/close cycles.
    """
    
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    pdf_name = Path(pdf_path).stem
    print(f"Starting memory-efficient section extraction from: {pdf_name}")
    
    # Get total page count
    total_pages = get_pdf_page_count(pdf_path)
    if total_pages == 0:
        return {
            'pdf_file': pdf_name,
            'error': 'Could not read PDF or PDF is empty',
            'success': False
        }
    
    print(f"PDF has {total_pages} pages, starting from page {start_page}")
    
    sections = []
    created_files = []
    current_page = start_page
    section_count = 0
    
    try:
        while current_page <= total_pages:
            print(f"\nSection {section_count + 1}: Starting at page {current_page}")
            
            # Extract next section (PDF opened and closed within this call)
            section, next_page = extract_next_section(pdf_path, current_page, total_pages)
            
            if section is None:
                print(f"  No more sections found, stopping at page {current_page}")
                break
            
            # Save section immediately
            section_file = save_section_immediately(section, output_dir, pdf_name)
            created_files.append(section_file)
            
            # Store section metadata (without full content to save memory)
            section_summary = {
                'title': section['section_title'],
                'id': section['section_id'],
                'start_page': section['start_page'],
                'end_page': section['end_page'],
                'character_count': section['character_count'],
                'word_count': section['word_count'],
                'file_path': section_file
            }
            sections.append(section_summary)
            
            print(f"  ✅ Saved: {section['section_title']} ({section['character_count']} chars)")
            
            # Move to next section
            current_page = next_page
            section_count += 1
            
            # Safety check to prevent infinite loops
            if section_count > 100:
                print(f"  Warning: Processed {section_count} sections, stopping for safety")
                break
        
        # Save overall summary
        summary = {
            'pdf_file': pdf_name,
            'success': True,
            'total_pages': total_pages,
            'start_page': start_page,
            'sections_found': len(sections),
            'sections': sections,
            'files_created': created_files
        }
        
        summary_file = os.path.join(output_dir, f"{pdf_name}_sections_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        created_files.append(summary_file)
        
        return summary
        
    except Exception as e:
        return {
            'pdf_file': pdf_name,
            'error': str(e),
            'success': False,
            'sections_processed': len(sections)
        }

def main():
    """Main CLI interface for memory-efficient section-based PDF extraction"""
    
    parser = argparse.ArgumentParser(
        description="Memory-efficient section extraction from PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all sections starting from page 1
  python extract-sections-memory-efficient.py data/players_book.pdf
  
  # Start from a specific page
  python extract-sections-memory-efficient.py data/players_book.pdf --start-page 15
  
  # Custom output directory
  python extract-sections-memory-efficient.py data/players_book.pdf --output-dir sections
        """
    )
    
    parser.add_argument(
        'pdf_file',
        help='PDF file to extract sections from'
    )
    
    parser.add_argument(
        '--start-page',
        type=int,
        default=1,
        help='Starting page number (default: 1)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory for section files (default: output)'
    )
    
    args = parser.parse_args()
    
    print("Memory-Efficient PDF Section Extraction")
    print("="*50)
    
    # Run extraction
    result = extract_all_sections(
        pdf_path=args.pdf_file,
        start_page=args.start_page,
        output_dir=args.output_dir
    )
    
    # Print results
    print(f"\n{'='*50}")
    print("EXTRACTION SUMMARY")
    print('='*50)
    
    if result.get('success'):
        print(f"✅ Success: {result['sections_found']} sections extracted")
        print(f"PDF: {result['pdf_file']} ({result['total_pages']} pages)")
        print(f"Files created: {len(result['files_created'])}")
        
        print(f"\nSections extracted:")
        for section in result['sections']:
            page_range = f"{section['start_page']}-{section['end_page']}"
            print(f"  • {section['title']}")
            print(f"    Pages: {page_range}, Characters: {section['character_count']}")
        
        print(f"\n📁 Section files saved to: {args.output_dir}/")
        print(f"📄 Summary: {args.output_dir}/{result['pdf_file']}_sections_summary.json")
        
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        if 'sections_processed' in result:
            print(f"Sections processed before failure: {result['sections_processed']}")
        sys.exit(1)

if __name__ == "__main__":
    main()