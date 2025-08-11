# PyMuPDF4LLM Data Structures and Output Formats

## Overview

PyMuPDF4LLM is **not just a markdown generator** - it's a sophisticated PDF data extraction engine that produces rich intermediate data structures. While it renders markdown by default, you have full access to the structured data and can generate any output format.

## Key Finding

**PyMuPDF4LLM does the hard work of spatial analysis and layout detection, then gives you structured data to render however you want.**

## Two Output Modes

### 1. Unified Markdown String (Default)
```python
result = pymupdf4llm.to_markdown(doc, page_chunks=False)
# Returns: string (concatenated markdown text)
```

### 2. Structured Page Data (Rich Format)
```python
result = pymupdf4llm.to_markdown(doc, page_chunks=True)
# Returns: List[dict] with detailed structure per page
```

## Structured Data Schema

When using `page_chunks=True`, each page returns:

```python
{
    "metadata": {
        "file_path": "document.pdf",
        "page_count": 100,
        "page": 15,
        "title": "...",        # From PDF metadata
        "author": "...",       # From PDF metadata
        "subject": "..."       # From PDF metadata
    },
    "toc_items": [
        [level, title, page_number], # Table of contents entries for this page
        [1, "Chapter 1", 15],
        [2, "Section 1.1", 15]
    ],
    "tables": [
        {
            "bbox": (x0, y0, x1, y1),  # Table position coordinates
            "rows": 5,                  # Number of table rows
            "columns": 3                # Number of table columns
        }
        # ... more tables on this page
    ],
    "images": [
        {
            "bbox": (x0, y0, x1, y1),  # Image position coordinates
            "width": 200,               # Image width
            "height": 150,              # Image height
            # ... additional PyMuPDF image metadata
        }
        # ... more images on this page
    ],
    "graphics": [],  # Vector graphics data (from page.get_drawings())
    
    "text": "# Header\n\nBody text...",  # Rendered markdown content
    
    "words": [  # Individual word positions (if extract_words=True)
        (x0, y0, x1, y1, "word", block_no, line_no, word_no),
        (72.0, 100.0, 95.0, 112.0, "Hello", 0, 0, 0),
        (97.0, 100.0, 125.0, 112.0, "World", 0, 0, 1)
        # ... more words with precise coordinates
    ]
}
```

## What PyMuPDF4LLM Provides

The structured data gives you access to PyMuPDF4LLM's sophisticated analysis:

### ✅ Spatial Analysis
- **Multi-column layout detection** - Identifies columns and proper reading order
- **Text block clustering** - Groups related text spatially
- **Element positioning** - Precise coordinates for all content

### ✅ Content Classification  
- **Table extraction** - Identifies and extracts table structure
- **Image detection** - Locates and describes images
- **Header detection** - Classifies text hierarchy
- **Vector graphics** - Identifies significant drawings/charts

### ✅ Document Structure
- **Reading order** - Proper sequence across multi-column layouts  
- **Table of contents** - Extracted TOC entries per page
- **Metadata preservation** - Document properties and page info

## Alternative Output Formats

Using the structured data, you can generate any format:

### JSON/JSONL for Databases
```python
pages = pymupdf4llm.to_markdown(doc, page_chunks=True, extract_words=True)

for page in pages:
    json_record = {
        'page_number': page['metadata']['page'],
        'content': page['text'], 
        'tables': page['tables'],
        'images': page['images'],
        'word_positions': page['words'],
        'toc_entries': page['toc_items']
    }
    # Store in database, output as JSONL, etc.
```

### HTML with Precise Positioning
```python  
def pages_to_html(pages):
    html = ["<html><body>"]
    
    for page in pages:
        html.append(f'<div class="page" data-page="{page["metadata"]["page"]}">')
        
        # Add images with absolute positioning
        for img in page['images']:
            x0, y0, x1, y1 = img['bbox']
            html.append(f'<img style="position:absolute; left:{x0}px; top:{y0}px; width:{x1-x0}px; height:{y1-y0}px">')
            
        # Add tables with positioning
        for table in page['tables']:
            x0, y0, x1, y1 = table['bbox']
            html.append(f'<div class="table" style="position:absolute; left:{x0}px; top:{y0}px">')
            html.append(f'<!-- {table["rows"]}x{table["columns"]} table -->')
            html.append('</div>')
            
        # Convert markdown content to HTML
        html.append(markdown.markdown(page['text']))
        html.append('</div>')
        
    html.append("</body></html>")
    return '\n'.join(html)
```

### LaTeX with Structure Preservation
```python
def pages_to_latex(pages):
    latex = ["\\documentclass{article}", "\\usepackage{graphicx}", "\\begin{document}"]
    
    for page in pages:
        # Convert markdown headers to LaTeX sections
        text = page['text']
        text = re.sub(r'^# (.+)$', r'\\section{\1}', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'\\subsection{\1}', text, flags=re.MULTILINE)
        text = re.sub(r'^### (.+)$', r'\\subsubsection{\1}', text, flags=re.MULTILINE)
        
        latex.append(text)
        
        # Add tables
        for table in page['tables']:
            latex.append(f"% Table: {table['rows']}x{table['columns']}")
            latex.append("\\begin{tabular}{" + "c" * table['columns'] + "}")
            latex.append("% Table content would go here")
            latex.append("\\end{tabular}")
            
        latex.append("\\newpage")
        
    latex.append("\\end{document}")
    return '\n'.join(latex)
```

### Spatial JSON for Layout Analysis
```python
def pages_to_spatial_json(pages):
    """Preserve exact positioning for layout analysis applications."""
    result = []
    
    for page in pages:
        page_data = {
            'page': page['metadata']['page'],
            'dimensions': None,  # Could extract from page.rect if needed
            'regions': []
        }
        
        # Add word-level regions with precise positions
        if page['words']:
            for word in page['words']:
                x0, y0, x1, y1, text, block, line, word_idx = word
                page_data['regions'].append({
                    'type': 'text',
                    'bbox': [x0, y0, x1, y1],
                    'content': text,
                    'block_id': block,
                    'line_id': line,
                    'word_id': word_idx
                })
        
        # Add table regions  
        for i, table in enumerate(page['tables']):
            page_data['regions'].append({
                'type': 'table',
                'bbox': list(table['bbox']),
                'table_id': i,
                'rows': table['rows'],
                'columns': table['columns']
            })
            
        # Add image regions
        for i, img in enumerate(page['images']):
            page_data['regions'].append({
                'type': 'image',
                'bbox': list(img['bbox']),
                'image_id': i,
                'width': img.get('width'),
                'height': img.get('height')
            })
            
        result.append(page_data)
    
    return result
```

### Custom Vector Database Format
```python
def pages_to_vector_chunks(pages, chunk_strategy='paragraph'):
    """Convert to chunks suitable for vector databases."""
    chunks = []
    
    for page in pages:
        page_num = page['metadata']['page']
        text = page['text']
        
        # Split into semantic chunks
        if chunk_strategy == 'paragraph':
            paragraphs = text.split('\n\n')
            for i, para in enumerate(paragraphs):
                if para.strip():
                    chunks.append({
                        'id': f"page_{page_num}_para_{i}",
                        'content': para,
                        'metadata': {
                            'page': page_num,
                            'paragraph': i,
                            'has_tables': len(page['tables']) > 0,
                            'has_images': len(page['images']) > 0,
                            'file_path': page['metadata']['file_path']
                        }
                    })
        
        # Add table content as separate chunks
        for i, table in enumerate(page['tables']):
            chunks.append({
                'id': f"page_{page_num}_table_{i}",
                'content': f"Table ({table['rows']}x{table['columns']}) at position {table['bbox']}",
                'metadata': {
                    'page': page_num,
                    'type': 'table',
                    'bbox': table['bbox'],
                    'rows': table['rows'],
                    'columns': table['columns']
                }
            })
    
    return chunks
```

## Usage Examples

### Basic Structured Extraction
```python
import pymupdf
import pymupdf4llm

def extract_structured_data(pdf_path, pages=None):
    """Extract rich structured data from PDF."""
    doc = pymupdf.open(pdf_path)
    
    structured_data = pymupdf4llm.to_markdown(
        doc,
        pages=pages,
        page_chunks=True,        # Get structured format
        extract_words=True,      # Include word positions
        ignore_images=False,     # Keep image data
        table_strategy="lines_strict"  # Better table detection
    )
    
    doc.close()
    return structured_data

# Usage
pages = extract_structured_data("document.pdf", pages=[0, 1, 2])
print(f"Extracted {len(pages)} pages")
print(f"Page 1 has {len(pages[0]['tables'])} tables and {len(pages[0]['images'])} images")
```

### Multi-Format Generator
```python
def extract_all_formats(pdf_path):
    """Extract PDF and generate multiple output formats."""
    doc = pymupdf.open(pdf_path)
    
    # Get structured data
    pages = pymupdf4llm.to_markdown(
        doc, 
        page_chunks=True,
        extract_words=True,
        ignore_images=False
    )
    
    # Generate multiple formats
    results = {
        'structured_data': pages,
        'markdown': '\n\n'.join(page['text'] for page in pages),
        'html': pages_to_html(pages),
        'latex': pages_to_latex(pages),
        'spatial_json': pages_to_spatial_json(pages),
        'vector_chunks': pages_to_vector_chunks(pages)
    }
    
    doc.close()
    return results
```

## Key Advantages

1. **Leverage Existing Sophistication**: PyMuPDF4LLM handles complex spatial analysis, multi-column detection, and table extraction
2. **Multiple Output Options**: Generate any format from the same structured data
3. **Preserve Spatial Information**: Access precise coordinates for layout-aware applications  
4. **Rich Metadata**: Full access to document properties, TOC, and element classification
5. **Extensible**: Build custom renderers for domain-specific needs

## Integration with Dolmenwood Project

For the Dolmenwood extraction project, this means:

1. **Use `page_chunks=True`** to get structured data
2. **Access precise positioning** for layout detection
3. **Generate multiple formats** from single extraction
4. **Preserve table and image data** for comprehensive content management
5. **Build custom renderers** for MCP server integration

## Files to Create

- `pymupdf4llm_extractors.py`: Custom format generators
- `structured_data_processors.py`: Tools for working with the structured format
- `multi_format_converter.py`: Unified interface for generating different outputs

This approach transforms PyMuPDF4LLM from a markdown generator into a comprehensive PDF data extraction platform.