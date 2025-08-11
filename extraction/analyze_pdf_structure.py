#!/usr/bin/env python3
"""
Analyzes the structure of a PDF to report on text extraction opportunities.
Provides insights into Table of Contents, page content, and semantic structure.
"""

import pymupdf4llm
import fitz  # PyMuPDF
import argparse
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

def get_pdf_toc(pdf_path: str) -> List[Dict[str, Any]]:
    """Extracts the Table of Contents from a PDF."""
    toc_data = []
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()
        doc.close()
        for level, title, page in toc:
            toc_data.append({"level": level, "title": title, "page": page})
    except Exception as e:
        print(f"Could not extract ToC: {e}")
    return toc_data

def find_section_header_in_text(text: str) -> Optional[Tuple[str, int, int]]:
    """Finds the first section header (any # level) in markdown text."""
    for i, line in enumerate(text.split('\n')):
        match = re.match(r'^(#+)\s+(.+)', line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            return title, i, level
    return None

def analyze_header_consistency(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes consistency of header detection across pages."""
    header_info = {
        "total_headers_found": 0,
        "pages_with_headers": 0,
        "header_levels": {},
        "consistent_level": None,
        "reliability_score": 0.0
    }
    
    for page in analysis_data["page_analysis"]:
        if page.get("header_info"):
            header_info["total_headers_found"] += 1
            header_info["pages_with_headers"] += 1
            level = page["header_info"][2]
            header_info["header_levels"][level] = header_info["header_levels"].get(level, 0) + 1
    
    # Determine most common header level
    if header_info["header_levels"]:
        most_common_level = max(header_info["header_levels"], key=header_info["header_levels"].get)
        header_info["consistent_level"] = most_common_level
        
        # Calculate reliability score based on consistency
        total_pages = len(analysis_data["page_analysis"])
        pages_with_consistent_headers = header_info["header_levels"][most_common_level]
        header_info["reliability_score"] = pages_with_consistent_headers / total_pages
    
    return header_info

def analyze_pdf_page(
    pdf_path: str,
    page_num: int
) -> Dict[str, Any]:
    """Analyzes a single page of a PDF for content and structure."""
    page_analysis = {
        "page_number": page_num,
        "character_count": 0,
        "word_count": 0,
        "image_count": 0,
        "header": None,
        "header_info": None,
        "text_snippet": ""
    }
    try:
        # Use pymupdf4llm for text extraction to match existing scripts
        result = pymupdf4llm.to_markdown(pdf_path, pages=[page_num], page_chunks=True)
        if result:
            page_data = result[0]
            text = page_data.get('text', '')
            page_analysis["character_count"] = len(text)
            page_analysis["word_count"] = len(text.split())
            page_analysis["text_snippet"] = text[:200].replace('\n', ' ') + "..."
            
            header_info = find_section_header_in_text(text)
            if header_info:
                page_analysis["header"] = header_info[0]
                page_analysis["header_info"] = header_info

        # Use fitz for image counting
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num - 1)
        page_analysis["image_count"] = len(page.get_images(full=True))
        doc.close()

    except Exception as e:
        page_analysis["error"] = str(e)

    return page_analysis

def analyze_pdf_structure(
    pdf_path: str,
    limit_pages: Optional[int] = None
) -> Dict[str, Any]:
    """
    Performs a full analysis of the PDF structure.
    """
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"Analyzing PDF: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    analysis_summary = {
        "pdf_file": Path(pdf_path).name,
        "total_pages": total_pages,
        "table_of_contents": get_pdf_toc(pdf_path),
        "page_analysis": []
    }

    pages_to_analyze = range(1, (limit_pages or total_pages) + 1)

    for page_num in pages_to_analyze:
        print(f"  Analyzing page {page_num}/{total_pages}...")
        page_report = analyze_pdf_page(pdf_path, page_num)
        analysis_summary["page_analysis"].append(page_report)

    # Add method recommendations
    analysis_summary["header_analysis"] = analyze_header_consistency(analysis_summary)
    analysis_summary["extraction_recommendations"] = recommend_extraction_methods(analysis_summary)

    return analysis_summary

def recommend_extraction_methods(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Recommends the best extraction methods based on PDF structure analysis."""
    recommendations = {
        "primary_method": None,
        "secondary_method": None,
        "methods": {
            "toc_based": {"viable": False, "score": 0.0, "reason": ""},
            "header_based": {"viable": False, "score": 0.0, "reason": ""},
            "page_based": {"viable": True, "score": 0.5, "reason": "Always available as fallback"}
        }
    }
    
    # Analyze TOC viability
    toc = analysis_data.get("table_of_contents", [])
    if toc:
        toc_score = min(len(toc) / 10, 1.0)  # More TOC entries = better score
        recommendations["methods"]["toc_based"]["viable"] = True
        recommendations["methods"]["toc_based"]["score"] = toc_score
        recommendations["methods"]["toc_based"]["reason"] = f"TOC found with {len(toc)} entries"
    else:
        recommendations["methods"]["toc_based"]["reason"] = "No TOC found in PDF"
    
    # Analyze header-based viability
    header_analysis = analysis_data.get("header_analysis", {})
    reliability = header_analysis.get("reliability_score", 0.0)
    if reliability > 0.3:  # At least 30% of pages have headers
        recommendations["methods"]["header_based"]["viable"] = True
        recommendations["methods"]["header_based"]["score"] = reliability
        recommendations["methods"]["header_based"]["reason"] = f"Headers found on {reliability:.1%} of pages"
    else:
        recommendations["methods"]["header_based"]["reason"] = f"Inconsistent headers ({reliability:.1%} coverage)"
    
    # Determine primary and secondary methods
    viable_methods = [(name, data) for name, data in recommendations["methods"].items() if data["viable"]]
    viable_methods.sort(key=lambda x: x[1]["score"], reverse=True)
    
    if viable_methods:
        recommendations["primary_method"] = viable_methods[0][0]
        if len(viable_methods) > 1:
            recommendations["secondary_method"] = viable_methods[1][0]
    
    return recommendations

def print_analysis_report(analysis: Dict[str, Any]):
    """Prints a human-readable report of the PDF analysis."""
    print("\n" + "="*60)
    print(f"PDF Structure Analysis Report for: {analysis['pdf_file']}")
    print("="*60)

    # Print ToC
    if analysis["table_of_contents"]:
        print("\n--- Table of Contents ---")
        for item in analysis["table_of_contents"]:
            indent = "  " * (item['level'] - 1)
            print(f"{indent}{item['title']} (p. {item['page']})")
    else:
        print("\n--- No Table of Contents Found ---")

    # Print Page-by-Page Analysis
    print("\n--- Page-by-Page Analysis ---")
    for page_report in analysis["page_analysis"]:
        print(f"\n- Page {page_report['page_number']}:")
        if "error" in page_report:
            print(f"  Error: {page_report['error']}")
            continue
        
        print(f"  - Stats: {page_report['character_count']} chars, {page_report['word_count']} words, {page_report['image_count']} images")
        if page_report['header']:
            print(f"  - Detected Header: '{page_report['header']}'")
        if page_report['text_snippet']:
            print(f"  - Snippet: {page_report['text_snippet']}")

    # Print Extraction Opportunities
    print("\n" + "="*60)
    print("Extraction Opportunities")
    print("="*60)
    text_heavy_pages = [p for p in analysis['page_analysis'] if p.get('character_count', 0) > 500]
    image_heavy_pages = [p for p in analysis['page_analysis'] if p.get('image_count', 0) > 0]
    header_pages = [p for p in analysis['page_analysis'] if p.get('header')]

    print(f"\n- Good candidates for text extraction ({len(text_heavy_pages)} pages with >500 chars):")
    print(f"  Pages: {[p['page_number'] for p in text_heavy_pages]}")

    print(f"\n- Pages with detected headers ({len(header_pages)} pages), useful for semantic chunking:")
    print(f"  Pages: {[p['page_number'] for p in header_pages]}")

    print(f"\n- Pages with images ({len(image_heavy_pages)} pages), may require OCR or image extraction:")
    print(f"  Pages: {[p['page_number'] for p in image_heavy_pages]}")

    # Print extraction method recommendations
    if "extraction_recommendations" in analysis:
        recommendations = analysis["extraction_recommendations"]
        print("\n" + "="*60)
        print("Extraction Method Recommendations")
        print("="*60)
        
        print(f"\nPrimary recommendation: {recommendations.get('primary_method', 'None')}")
        if recommendations.get('secondary_method'):
            print(f"Secondary recommendation: {recommendations['secondary_method']}")
        
        print("\nMethod Analysis:")
        for method, data in recommendations["methods"].items():
            status = "✓ VIABLE" if data["viable"] else "✗ Not viable"
            score = f"(Score: {data['score']:.2f})" if data["viable"] else ""
            print(f"  - {method.replace('_', ' ').title()}: {status} {score}")
            print(f"    {data['reason']}")

    # Print header analysis details
    if "header_analysis" in analysis:
        header_info = analysis["header_analysis"]
        print(f"\nHeader Detection Details:")
        print(f"  - Total headers found: {header_info['total_headers_found']}")
        print(f"  - Pages with headers: {header_info['pages_with_headers']}")
        print(f"  - Reliability score: {header_info['reliability_score']:.2f}")
        if header_info["header_levels"]:
            print(f"  - Header levels found: {dict(header_info['header_levels'])}")
            print(f"  - Most consistent level: #{header_info['consistent_level']}")


def main():
    """Main CLI interface for PDF structure analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze PDF structure for text extraction opportunities.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  # Analyze the first 20 pages of a PDF
  python analyze_pdf_structure.py path/to/book.pdf --limit-pages 20
        """
    )
    parser.add_argument('pdf_file', help='PDF file to analyze')
    parser.add_argument('--limit-pages', type=int, help='Limit analysis to the first N pages')
    parser.add_argument('--output-json', help='Save analysis to a JSON file')

    args = parser.parse_args()

    try:
        analysis = analyze_pdf_structure(args.pdf_file, args.limit_pages)
        print_analysis_report(analysis)

        if args.output_json:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            print(f"\nAnalysis saved to {args.output_json}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
