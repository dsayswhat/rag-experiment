#!/usr/bin/env python3
"""
Production-ready PDF text extraction using PyMuPDF4LLM.
Optimized for Dolmenwood RPG materials and LLM processing.
"""

import pymupdf4llm
import json
import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any

def make_json_serializable(obj):
    """Convert PyMuPDF objects to JSON-serializable format"""
    if hasattr(obj, '__dict__'):
        # For objects with attributes, convert to dict
        return {k: make_json_serializable(v) for k, v in obj.__dict__.items()}
    elif hasattr(obj, 'x0') and hasattr(obj, 'y0'):
        # For Rect-like objects, convert to coordinate dict
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
        # For other objects, convert to string representation
        return str(obj)

def extract_pdf_text(
    pdf_path: str,
    pages: Optional[List[int]] = None,
    output_format: str = "markdown",
    include_images: bool = False,
    image_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract text from PDF using PyMuPDF4LLM with production settings.
    
    Args:
        pdf_path: Path to PDF file
        pages: List of page numbers as specified by user, None for all pages
        output_format: 'markdown' or 'json'
        include_images: Whether to extract images
        image_path: Directory to save extracted images
    
    Returns:
        Dictionary with extraction results
    """
    
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    print(f"Extracting from: {Path(pdf_path).name}")
    if pages:
        print(f"Pages: {pages}")
    else:
        print("Pages: All")
    
    try:
        # Extract with PyMuPDF4LLM
        result = pymupdf4llm.to_markdown(
            pdf_path,
            pages=pages,
            page_chunks=True,  # Always use page chunks for structured output
            write_images=include_images,
            image_path=image_path,
            image_format="png",
            dpi=150
        )
        
        # Process results
        extraction_info = {
            'source_file': str(Path(pdf_path).name),
            'extraction_method': 'PyMuPDF4LLM',
            'pages_extracted': len(result),
            'total_characters': sum(len(page.get('text', '')) for page in result),
            'pages': []
        }
        
        for i, page_data in enumerate(result):
            page_info = {
                'page_number': pages[i] if pages else (i + 1),
                'character_count': len(page_data.get('text', '')),
                'word_count': len(page_data.get('text', '').split()),
                'line_count': len(page_data.get('text', '').split('\n')),
                'has_content': bool(page_data.get('text', '').strip()),
                'metadata': make_json_serializable({k: v for k, v in page_data.items() if k != 'text'})
            }
            
            if output_format == "json":
                page_info['text'] = page_data.get('text', '')
            else:
                # For markdown output, we'll save text separately
                page_info['text_length'] = len(page_data.get('text', ''))
            
            extraction_info['pages'].append(page_info)
            
            print(f"  Page {page_info['page_number']}: {page_info['character_count']} chars")
        
        # Add the actual text data
        if output_format == "markdown":
            extraction_info['markdown_pages'] = [page.get('text', '') for page in result]
        
        return extraction_info
        
    except Exception as e:
        error_info = {
            'source_file': str(Path(pdf_path).name),
            'extraction_method': 'PyMuPDF4LLM',
            'error': str(e),
            'success': False
        }
        print(f"Extraction failed: {e}")
        return error_info

def save_extraction_results(
    results: Dict[str, Any],
    output_dir: str,
    base_filename: str,
    save_individual_pages: bool = True
) -> List[str]:
    """
    Save extraction results to files.
    
    Returns:
        List of created file paths
    """
    
    os.makedirs(output_dir, exist_ok=True)
    created_files = []
    
    # Save JSON metadata
    json_file = os.path.join(output_dir, f"{base_filename}_extraction_info.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        # Remove markdown_pages from JSON to avoid duplication
        json_data = {k: v for k, v in results.items() if k != 'markdown_pages'}
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    created_files.append(json_file)
    
    # Save full markdown text
    if 'markdown_pages' in results:
        markdown_file = os.path.join(output_dir, f"{base_filename}_full_text.md")
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(f"# {results.get('source_file', 'PDF')} - Extracted Text\n\n")
            f.write(f"**Extraction Method:** {results.get('extraction_method', 'Unknown')}\n")
            f.write(f"**Pages Extracted:** {results.get('pages_extracted', 0)}\n")
            f.write(f"**Total Characters:** {results.get('total_characters', 0)}\n\n")
            f.write("---\n\n")
            
            for i, page_text in enumerate(results['markdown_pages']):
                page_num = results['pages'][i]['page_number']
                f.write(f"## Page {page_num}\n\n")
                f.write(page_text)
                f.write("\n\n---\n\n")
        
        created_files.append(markdown_file)
    
    # Save individual page files if requested
    if save_individual_pages and 'markdown_pages' in results:
        for i, page_text in enumerate(results['markdown_pages']):
            page_num = results['pages'][i]['page_number']
            page_file = os.path.join(output_dir, f"{base_filename}_page_{page_num:03d}.md")
            
            with open(page_file, 'w', encoding='utf-8') as f:
                f.write(f"# Page {page_num}\n\n")
                f.write(f"**Source:** {results.get('source_file', 'Unknown')}\n")
                f.write(f"**Characters:** {results['pages'][i]['character_count']}\n")
                f.write(f"**Words:** {results['pages'][i]['word_count']}\n\n")
                f.write("---\n\n")
                f.write(page_text)
            
            created_files.append(page_file)
    
    return created_files

def extract_dolmenwood_pdfs(
    pdf_paths: List[str],
    output_dir: str,
    pages: Optional[List[int]] = None,
    include_images: bool = False
) -> Dict[str, Any]:
    """
    Extract text from multiple Dolmenwood PDFs.
    
    Returns:
        Summary of all extractions
    """
    
    summary = {
        'total_pdfs_processed': 0,
        'successful_extractions': 0,
        'failed_extractions': 0,
        'results': {},
        'created_files': []
    }
    
    for pdf_path in pdf_paths:
        pdf_name = Path(pdf_path).stem
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_name}")
        print('='*60)
        
        try:
            # Extract text
            image_path = os.path.join(output_dir, "images", pdf_name) if include_images else None
            
            results = extract_pdf_text(
                pdf_path=pdf_path,
                pages=pages,
                output_format="markdown",
                include_images=include_images,
                image_path=image_path
            )
            
            if 'error' not in results:
                # Save results
                created_files = save_extraction_results(
                    results=results,
                    output_dir=output_dir,
                    base_filename=pdf_name,
                    save_individual_pages=True
                )
                
                summary['successful_extractions'] += 1
                summary['results'][pdf_name] = {
                    'status': 'success',
                    'pages_extracted': results.get('pages_extracted', 0),
                    'total_characters': results.get('total_characters', 0),
                    'files_created': created_files
                }
                summary['created_files'].extend(created_files)
                
                print(f"✅ Success: {results.get('pages_extracted', 0)} pages, {results.get('total_characters', 0)} characters")
                
            else:
                summary['failed_extractions'] += 1
                summary['results'][pdf_name] = {
                    'status': 'failed',
                    'error': results.get('error', 'Unknown error')
                }
                print(f"❌ Failed: {results.get('error', 'Unknown error')}")
        
        except Exception as e:
            summary['failed_extractions'] += 1
            summary['results'][pdf_name] = {
                'status': 'failed',
                'error': str(e)
            }
            print(f"❌ Failed: {e}")
        
        summary['total_pdfs_processed'] += 1
    
    return summary

def main():
    """Main CLI interface for production PDF extraction"""
    
    parser = argparse.ArgumentParser(
        description="Extract text from Dolmenwood PDFs using PyMuPDF4LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all pages from a single PDF
  python production_extract.py path/to/book.pdf
  
  # Extract specific pages (1-indexed)
  python production_extract.py path/to/book.pdf --pages 11 12 13
  
  # Extract from multiple PDFs
  python production_extract.py book1.pdf book2.pdf book3.pdf
  
  # Extract with images
  python production_extract.py path/to/book.pdf --images
        """
    )
    
    parser.add_argument(
        'pdf_files',
        nargs='+',
        help='PDF file(s) to extract text from'
    )
    
    parser.add_argument(
        '--pages',
        type=int,
        nargs='+',
        help='Specific page numbers to extract (1-indexed). If not specified, extracts all pages.'
    )
    
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory for extracted text files (default: output)'
    )
    
    parser.add_argument(
        '--images',
        action='store_true',
        help='Extract images from PDFs'
    )
    
    args = parser.parse_args()
    
    # Use pages as specified by user (no conversion)
    pages = args.pages if args.pages else None
    
    # Validate PDF files
    valid_pdfs = []
    for pdf_path in args.pdf_files:
        if Path(pdf_path).exists():
            valid_pdfs.append(pdf_path)
        else:
            print(f"Warning: PDF not found: {pdf_path}")
    
    if not valid_pdfs:
        print("Error: No valid PDF files found")
        sys.exit(1)
    
    # Run extraction
    print("PyMuPDF4LLM PDF Text Extraction")
    print("="*40)
    print(f"PDFs to process: {len(valid_pdfs)}")
    print(f"Output directory: {args.output_dir}")
    if pages:
        print(f"Pages to extract: {pages}")
    else:
        print("Pages to extract: All")
    print(f"Extract images: {args.images}")
    
    summary = extract_dolmenwood_pdfs(
        pdf_paths=valid_pdfs,
        output_dir=args.output_dir,
        pages=pages,
        include_images=args.images
    )
    
    # Save summary
    summary_file = os.path.join(args.output_dir, "extraction_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print final summary
    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print('='*60)
    print(f"Total PDFs processed: {summary['total_pdfs_processed']}")
    print(f"Successful extractions: {summary['successful_extractions']}")
    print(f"Failed extractions: {summary['failed_extractions']}")
    print(f"Total files created: {len(summary['created_files'])}")
    print(f"Summary saved to: {summary_file}")
    
    if summary['successful_extractions'] > 0:
        print(f"\n📁 Output files saved to: {args.output_dir}/")
        print("✅ Extraction complete!")
    else:
        print("\n❌ No successful extractions")
        sys.exit(1)

if __name__ == "__main__":
    main()