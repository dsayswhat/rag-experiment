# PyMuPDF4LLM Enhancement Guide

This document describes how to use PyMuPDF4LLM as a library and enhance it with custom domain-specific logic for better Dolmenwood PDF extraction.

## Overview

PyMuPDF4LLM provides sophisticated PDF layout analysis but uses generic header detection based solely on font sizes. For Dolmenwood PDFs with color-coded headers, illuminated letters, and complex layouts, we can enhance their approach with domain-specific intelligence.

## Library Architecture

PyMuPDF4LLM is designed to be extensible. Key components:

- **`to_markdown()`**: Main extraction function that accepts custom header detection
- **`IdentifyHeaders`**: Default font-size-based header detection class  
- **`column_boxes()`**: Spatial layout analysis and multi-column detection
- **Custom header detection**: Any object with `get_header_id(span, page)` method

## Enhancement Strategy

### 1. Custom Header Detection Class

Replace PyMuPDF4LLM's font-size-only approach with color and context-aware detection:

```python
import pymupdf
import pymupdf4llm
from collections import defaultdict, Counter

class DolmenwoodHeaderDetector:
    """Enhanced header detection for Dolmenwood PDFs using color, size, and context."""
    
    def __init__(self, doc, pages=None):
        """
        Initialize with document analysis to learn color patterns.
        
        Args:
            doc: PyMuPDF Document object
            pages: List of pages to analyze (None for all pages)
        """
        self.doc = doc
        self.pages = pages or list(range(doc.page_count))
        
        # Analyze document to learn patterns
        self.color_patterns = self._analyze_color_patterns()
        self.font_patterns = self._analyze_font_patterns() 
        self.position_patterns = self._analyze_position_patterns()
        
        # Classification rules learned from analysis
        self.header_colors = self._identify_header_colors()
        self.body_text_size = self._identify_body_text_size()
        
    def _analyze_color_patterns(self):
        """Analyze all text colors in the document to identify header colors."""
        color_usage = defaultdict(list)  # color -> [(size, text, position), ...]
        
        for page_num in self.pages:
            page = self.doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block.get('type') != 0:  # Skip non-text blocks
                    continue
                    
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        color = span.get('color', 0)
                        size = span.get('size', 0)
                        text = span.get('text', '').strip()
                        bbox = span.get('bbox', [0, 0, 0, 0])
                        
                        if text and size > 0:
                            color_hex = f"#{color:06x}" if color != 0 else "#000000"
                            color_usage[color_hex].append({
                                'size': size,
                                'text': text,
                                'bbox': bbox,
                                'page': page_num
                            })
        
        return color_usage
    
    def _analyze_font_patterns(self):
        """Analyze font sizes and styles to identify hierarchical patterns."""
        size_usage = Counter()
        style_patterns = defaultdict(list)
        
        for page_num in self.pages:
            page = self.doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block.get('type') != 0:
                    continue
                    
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        size = round(span.get('size', 0), 1)
                        text = span.get('text', '').strip()
                        flags = span.get('flags', 0)
                        
                        if text:
                            size_usage[size] += len(text)
                            
                            # Decode style flags
                            is_bold = bool(flags & (1 << 4))
                            is_italic = bool(flags & (1 << 1))
                            
                            style_patterns[size].append({
                                'text': text[:100],  # Truncate for analysis
                                'bold': is_bold,
                                'italic': is_italic,
                                'page': page_num
                            })
        
        return {'sizes': size_usage, 'styles': style_patterns}
    
    def _analyze_position_patterns(self):
        """Analyze text positioning to identify layout patterns."""
        position_data = []
        
        for page_num in self.pages:
            page = self.doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block.get('type') != 0:
                    continue
                    
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        bbox = span.get('bbox', [0, 0, 0, 0])
                        text = span.get('text', '').strip()
                        size = span.get('size', 0)
                        
                        if text and size > 0:
                            position_data.append({
                                'x0': bbox[0], 'y0': bbox[1],
                                'x1': bbox[2], 'y1': bbox[3],
                                'text': text,
                                'size': size,
                                'page': page_num
                            })
        
        return position_data
    
    def _identify_header_colors(self):
        """Identify which colors are likely to be headers vs body text."""
        header_colors = {
            'primary': [],    # Main section headers (orange in Dolmenwood)
            'secondary': [],  # Subsection headers (brown in Dolmenwood) 
            'tertiary': []    # Minor headers
        }
        
        # Analyze color patterns to classify
        for color, usage_list in self.color_patterns.items():
            avg_size = sum(item['size'] for item in usage_list) / len(usage_list)
            text_samples = [item['text'] for item in usage_list[:10]]  # Sample texts
            
            # Heuristics for header detection:
            # 1. Larger than body text
            # 2. Often short phrases/single words
            # 3. May be ALL CAPS or Title Case
            # 4. Less frequent than body text
            
            if avg_size > self.body_text_size * 1.2:  # Significantly larger
                avg_length = sum(len(text) for text in text_samples) / len(text_samples)
                caps_ratio = sum(1 for text in text_samples if text.isupper()) / len(text_samples)
                
                if avg_length < 30 and (caps_ratio > 0.3 or avg_size > self.body_text_size * 1.5):
                    if avg_size > self.body_text_size * 2:
                        header_colors['primary'].append(color)
                    elif avg_size > self.body_text_size * 1.5:
                        header_colors['secondary'].append(color)
                    else:
                        header_colors['tertiary'].append(color)
        
        return header_colors
    
    def _identify_body_text_size(self):
        """Identify the most common font size (body text)."""
        if not self.font_patterns['sizes']:
            return 12.0  # Default fallback
        
        # Most frequent size by character count
        return max(self.font_patterns['sizes'], key=self.font_patterns['sizes'].get)
    
    def is_illuminated_letter(self, span, page=None):
        """Detect illuminated letters (large decorative first letters)."""
        text = span.get('text', '').strip()
        size = span.get('size', 0)
        
        # Characteristics of illuminated letters:
        # 1. Single character or very short
        # 2. Much larger than body text
        # 3. Often at the start of paragraphs
        
        if (len(text) <= 2 and 
            size > self.body_text_size * 2 and
            text.isalpha()):
            return True
        
        return False
    
    def classify_by_context(self, span, page=None):
        """Use content context to classify headers."""
        text = span.get('text', '').strip()
        
        # Known Dolmenwood section types
        dolmenwood_classes = {'Thief', 'Fighter', 'Cleric', 'Magic-User', 'Druid', 'Knight'}
        dolmenwood_skills = {'BACK-STAB', 'THIEF SKILLS', 'SPELLS', 'TURNING UNDEAD'}
        
        if text in dolmenwood_classes:
            return "# "  # Main class headers
        elif text in dolmenwood_skills or text.isupper():
            return "## " # Skill/ability headers
        elif text.startswith('**') and text.endswith('**'):
            return "### " # Bold subsection headers
        
        return None
    
    def get_header_id(self, span, page=None):
        """
        Main method called by PyMuPDF4LLM to classify text as header or body.
        
        Args:
            span: Text span dictionary from PyMuPDF
            page: Page object (optional)
            
        Returns:
            String: Markdown header prefix ("# ", "## ", etc.) or empty string for body text
        """
        # Skip illuminated letters
        if self.is_illuminated_letter(span, page):
            return ""
        
        # Try context-based classification first
        context_result = self.classify_by_context(span, page)
        if context_result:
            return context_result
        
        # Color-based classification
        color = span.get('color', 0)
        color_hex = f"#{color:06x}" if color != 0 else "#000000"
        
        if color_hex in self.header_colors['primary']:
            return "# "
        elif color_hex in self.header_colors['secondary']:  
            return "## "
        elif color_hex in self.header_colors['tertiary']:
            return "### "
        
        # Fallback to size-based classification
        size = span.get('size', 0)
        if size > self.body_text_size * 1.8:
            return "# "
        elif size > self.body_text_size * 1.4:
            return "## "
        elif size > self.body_text_size * 1.2:
            return "### "
        
        return ""  # Body text

    def get_analysis_report(self):
        """Generate a report of the document analysis for debugging."""
        report = []
        report.append("=== DOLMENWOOD PDF ANALYSIS REPORT ===\n")
        
        report.append(f"Body text size: {self.body_text_size}pt")
        report.append(f"Pages analyzed: {len(self.pages)}")
        report.append("")
        
        report.append("Color Usage:")
        for color, usage_list in self.color_patterns.items():
            avg_size = sum(item['size'] for item in usage_list) / len(usage_list)
            sample_text = usage_list[0]['text'][:50] if usage_list else "No text"
            report.append(f"  {color}: {len(usage_list)} instances, avg size {avg_size:.1f}pt")
            report.append(f"    Example: '{sample_text}'")
        
        report.append("")
        report.append("Header Color Classification:")
        for level, colors in self.header_colors.items():
            if colors:
                report.append(f"  {level}: {colors}")
        
        return "\n".join(report)
```

### 2. Usage Examples

#### Basic Usage with Custom Headers
```python
import pymupdf
import pymupdf4llm

# Open your PDF
doc = pymupdf.open("path/to/dolmenwood.pdf")

# Create custom header detector
header_detector = DolmenwoodHeaderDetector(doc, pages=[75, 76, 77, 78])  # Thief section

# Extract with custom headers
markdown_text = pymupdf4llm.to_markdown(
    doc,
    pages=[75, 76, 77, 78],
    hdr_info=header_detector,  # Use our custom detector
    page_chunks=False,
    ignore_images=False
)

# Optionally get analysis report
print(header_detector.get_analysis_report())

doc.close()
```

#### Advanced Usage with Layout Enhancement
```python
from pymupdf4llm.helpers.multi_column import column_boxes

def enhanced_extraction(doc, pages):
    """Combine custom header detection with enhanced layout analysis."""
    
    header_detector = DolmenwoodHeaderDetector(doc, pages)
    results = []
    
    for page_num in pages:
        page = doc[page_num]
        
        # Get PyMuPDF4LLM's spatial regions  
        regions = column_boxes(
            page,
            footer_margin=50,  # Ignore page numbers
            header_margin=30,  # Ignore running headers
            no_image_text=False  # Extract text from images too
        )
        
        # Extract text from each region with custom headers
        page_content = []
        for region in regions:
            region_text = page.get_text("dict", clip=region)
            
            # Process with custom header detection
            # (You'd implement region-specific processing here)
            page_content.append(region_text)
        
        # Use PyMuPDF4LLM's main extraction with custom headers
        page_markdown = pymupdf4llm.to_markdown(
            doc,
            pages=[page_num],
            hdr_info=header_detector,
            page_chunks=True,
            ignore_images=False
        )
        
        results.append({
            'page': page_num,
            'regions': regions,
            'markdown': page_markdown,
            'analysis': header_detector.get_analysis_report()
        })
    
    return results
```

### 3. Integration with Existing Extraction Pipeline

To integrate with your current extraction system:

```python
# In your existing extraction script
def extract_with_enhanced_headers(pdf_path, start_page, end_page):
    """Enhanced version of your current extraction."""
    
    doc = pymupdf.open(pdf_path)
    pages = list(range(start_page - 1, end_page))  # Convert to 0-based
    
    # Create domain-specific header detector
    header_detector = DolmenwoodHeaderDetector(doc, pages)
    
    # Use PyMuPDF4LLM with custom headers
    markdown_content = pymupdf4llm.to_markdown(
        doc,
        pages=pages,
        hdr_info=header_detector,
        page_chunks=False,
        page_separators=False,
        ignore_images=False,
        table_strategy="lines_strict",
        force_text=True
    )
    
    doc.close()
    return markdown_content, header_detector.get_analysis_report()
```

## Benefits of This Approach

1. **Leverage Existing Sophistication**: Keep PyMuPDF4LLM's multi-column detection, table extraction, and reading order logic
2. **Add Domain Intelligence**: Color recognition, illuminated letter handling, Dolmenwood terminology recognition
3. **Maintainable**: Built on top of a maintained library rather than custom implementation
4. **Debuggable**: Analysis reports help understand what the detector is finding
5. **Extensible**: Easy to add new rules as you discover more patterns

## Next Steps

1. **Test on sample pages**: Run the detector on known problematic pages
2. **Refine color detection**: Adjust thresholds based on actual Dolmenwood color patterns
3. **Add content-specific rules**: Recognize spell names, location types, stat blocks
4. **Handle edge cases**: Improve illuminated letter detection, table formatting, etc.

## Files to Create

- `dolmenwood_header_detector.py`: Main custom detector class
- `enhanced_extraction.py`: Integration with existing extraction pipeline  
- `test_header_detection.py`: Testing and validation scripts
- `analysis_reports/`: Directory for debugging output

This approach gives you the best of both worlds: PyMuPDF4LLM's robust foundation with Dolmenwood-specific intelligence layered on top.