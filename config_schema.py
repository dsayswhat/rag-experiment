#!/usr/bin/env python3
"""
Configuration schema for configurable PDF text extraction.

This module defines Pydantic models that validate extraction configuration files,
ensuring they contain all required fields with proper types and constraints.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any, Literal, Union
from enum import Enum
import re


class ReadingOrder(str, Enum):
    """Document reading order options."""
    LEFT_TO_RIGHT_TOP_TO_BOTTOM = "left_to_right_top_to_bottom"
    RIGHT_TO_LEFT_TOP_TO_BOTTOM = "right_to_left_top_to_bottom"
    TOP_TO_BOTTOM_LEFT_TO_RIGHT = "top_to_bottom_left_to_right"
    SINGLE_COLUMN = "single_column"


class OutputFormat(str, Enum):
    """Supported output formats."""
    STRUCTURED_JSON = "structured_json"
    MARKDOWN = "markdown"
    HTML = "html"
    CUSTOM = "custom"


class ChunkStrategy(str, Enum):
    """Content chunking strategies."""
    SEMANTIC_HEADERS = "semantic_headers"
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    PAGE = "page"
    NONE = "none"


class TableDetectionMethod(str, Enum):
    """Table detection methods for PyMuPDF4LLM."""
    LINES_STRICT = "lines_strict"
    LINES_RELAXED = "lines_relaxed"
    TEXT = "text"
    DISABLED = "disabled"


class SpecialElementAction(str, Enum):
    """Actions to take for special elements."""
    IGNORE = "ignore"
    PRESERVE = "preserve"
    CONVERT = "convert"
    EXTRACT = "extract"


class HeaderRule(BaseModel):
    """Configuration for detecting headers based on styling and content."""
    
    # Font styling criteria
    color: Optional[str] = Field(None, description="Hex color code (e.g., '#ff0000')")
    size_min: Optional[float] = Field(None, ge=6.0, le=72.0, description="Minimum font size in points")
    size_max: Optional[float] = Field(None, ge=6.0, le=72.0, description="Maximum font size in points")
    bold: Optional[bool] = Field(None, description="Must be bold (True) or not bold (False)")
    italic: Optional[bool] = Field(None, description="Must be italic (True) or not italic (False)")
    monospace: Optional[bool] = Field(None, description="Must be monospace font")
    
    # Content-based criteria
    context_patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns that text must match"
    )
    content_length_max: Optional[int] = Field(
        None, ge=1, description="Maximum character length for header text"
    )
    all_caps: Optional[bool] = Field(None, description="Must be all uppercase")
    title_case: Optional[bool] = Field(None, description="Must be title case")
    
    # Positional criteria
    position_x_min: Optional[float] = Field(None, description="Minimum X coordinate")
    position_x_max: Optional[float] = Field(None, description="Maximum X coordinate")
    indent_level: Optional[int] = Field(None, ge=0, description="Indentation level (0=no indent)")
    
    # Metadata
    description: Optional[str] = Field(None, description="Human-readable description of this rule")
    examples: List[str] = Field(default_factory=list, description="Example texts this rule should match")
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        """Validate hex color format."""
        if v is not None:
            if not re.match(r'^#[0-9a-fA-F]{6}$', v):
                raise ValueError('Color must be in hex format like #ff0000')
        return v
    
    @field_validator('context_patterns')
    @classmethod
    def validate_regex_patterns(cls, v):
        """Validate regex patterns compile correctly."""
        for pattern in v:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f'Invalid regex pattern "{pattern}": {e}')
        return v
    
    @model_validator(mode='after')
    def validate_size_range(self):
        """Ensure size_min <= size_max."""
        if self.size_min is not None and self.size_max is not None and self.size_min > self.size_max:
            raise ValueError('size_min must be less than or equal to size_max')
        return self


class HeaderRules(BaseModel):
    """Header detection rules organized by hierarchy level."""
    
    level_1: List[HeaderRule] = Field(default_factory=list, description="Primary headers (e.g., chapter titles)")
    level_2: List[HeaderRule] = Field(default_factory=list, description="Secondary headers (e.g., sections)")  
    level_3: List[HeaderRule] = Field(default_factory=list, description="Tertiary headers (e.g., subsections)")
    level_4: List[HeaderRule] = Field(default_factory=list, description="Fourth-level headers")
    level_5: List[HeaderRule] = Field(default_factory=list, description="Fifth-level headers")
    level_6: List[HeaderRule] = Field(default_factory=list, description="Sixth-level headers")
    
    @field_validator('level_1', 'level_2', 'level_3', 'level_4', 'level_5', 'level_6')
    @classmethod
    def validate_non_empty_rules(cls, v, info):
        """Ensure rules have at least one criterion."""
        for rule in v:
            criteria_count = sum(1 for attr in ['color', 'size_min', 'size_max', 'bold', 'italic', 
                                               'monospace', 'context_patterns', 'all_caps', 'title_case']
                                if getattr(rule, attr) is not None and getattr(rule, attr) != [])
            if criteria_count == 0:
                raise ValueError(f'{info.field_name} rules must have at least one detection criterion')
        return v


class IlluminatedLetters(BaseModel):
    """Configuration for handling illuminated letters (decorative first letters)."""
    
    enabled: bool = Field(True, description="Enable illuminated letter detection")
    size_threshold: float = Field(18.0, ge=12.0, description="Minimum font size to consider illuminated")
    max_length: int = Field(2, ge=1, le=5, description="Maximum character length")
    position: Literal["paragraph_start", "line_start", "any"] = Field(
        "paragraph_start", description="Where illuminated letters appear"
    )
    action: SpecialElementAction = Field(
        SpecialElementAction.IGNORE, description="How to handle detected illuminated letters"
    )
    patterns: List[str] = Field(
        default_factory=list, description="Additional regex patterns for detection"
    )


class StatBlocks(BaseModel):
    """Configuration for handling structured data like RPG stat blocks."""
    
    enabled: bool = Field(True, description="Enable stat block detection")
    patterns: List[str] = Field(
        default_factory=lambda: [
            r"^(STR|DEX|CON|INT|WIS|CHA):\s*\d+",
            r"^(AC|HD|HP):\s*[\d+/-]+",
            r"^\w+:\s*[^\n]{1,50}$"  # Generic key:value pattern
        ],
        description="Regex patterns that identify stat blocks"
    )
    formatting: Literal["preserve_structure", "convert_to_text", "extract_data"] = Field(
        "preserve_structure", description="How to format detected stat blocks"
    )
    multi_line: bool = Field(True, description="Allow stat blocks to span multiple lines")
    separator_patterns: List[str] = Field(
        default_factory=lambda: [r"[,;]", r"\n", r"\s{2,}"],
        description="Patterns that separate stat block entries"
    )


class Tables(BaseModel):
    """Configuration for table detection and extraction."""
    
    enabled: bool = Field(True, description="Enable table detection")
    detection_method: TableDetectionMethod = Field(
        TableDetectionMethod.LINES_STRICT, description="PyMuPDF4LLM table detection method"
    )
    preserve_formatting: bool = Field(True, description="Preserve table formatting in output")
    min_rows: int = Field(2, ge=1, description="Minimum rows to consider a table")
    min_columns: int = Field(2, ge=1, description="Minimum columns to consider a table")
    extract_to_csv: bool = Field(False, description="Extract tables to separate CSV data")


class Images(BaseModel):
    """Configuration for image handling."""
    
    enabled: bool = Field(True, description="Enable image detection")
    extract_images: bool = Field(False, description="Extract images to separate files")
    preserve_captions: bool = Field(True, description="Preserve image captions")
    min_size: Optional[int] = Field(None, ge=100, description="Minimum image size in pixels")
    formats: List[str] = Field(
        default_factory=lambda: ["png", "jpg", "jpeg"],
        description="Image formats to extract"
    )


class SpecialElements(BaseModel):
    """Configuration for handling special document elements."""
    
    illuminated_letters: IlluminatedLetters = Field(default_factory=IlluminatedLetters)
    stat_blocks: StatBlocks = Field(default_factory=StatBlocks)
    tables: Tables = Field(default_factory=Tables)
    images: Images = Field(default_factory=Images)


class DocumentAnalysis(BaseModel):
    """Document analysis settings derived from pdf_structure_analyzer.py."""
    
    body_text_size: float = Field(12.0, ge=6.0, le=24.0, description="Primary body text font size")
    column_detection: bool = Field(True, description="Enable multi-column layout detection")
    reading_order: ReadingOrder = Field(
        ReadingOrder.LEFT_TO_RIGHT_TOP_TO_BOTTOM, description="Document reading order"
    )
    ignore_headers: bool = Field(True, description="Ignore running headers")
    ignore_footers: bool = Field(True, description="Ignore running footers")
    header_margin: float = Field(30.0, ge=0.0, description="Top margin to ignore (pixels)")
    footer_margin: float = Field(50.0, ge=0.0, description="Bottom margin to ignore (pixels)")


class ContentFilters(BaseModel):
    """Patterns for filtering content during extraction."""
    
    ignore_patterns: List[str] = Field(
        default_factory=lambda: [
            r"^Page \d+$",  # Page numbers
            r"^\s*\d+\s*$",  # Standalone numbers
            r"^Chapter \d+$",  # Chapter markers
        ],
        description="Regex patterns for content to ignore completely"
    )
    preserve_patterns: List[str] = Field(
        default_factory=lambda: [
            r"\*\*.*\*\*",  # Bold markdown
            r"_.*_",        # Italic markdown
            r"`.*`",        # Code markdown
        ],
        description="Regex patterns for content to preserve exactly"
    )
    clean_patterns: Dict[str, str] = Field(
        default_factory=lambda: {
            r"\s{2,}": " ",      # Multiple spaces to single space
            r"\n{3,}": "\n\n",   # Multiple newlines to double newline
        },
        description="Find-replace patterns for cleaning content"
    )
    
    @field_validator('ignore_patterns', 'preserve_patterns')
    @classmethod
    def validate_regex_patterns(cls, v):
        """Validate regex patterns compile correctly."""
        for pattern in v:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f'Invalid regex pattern "{pattern}": {e}')
        return v


class OutputSettings(BaseModel):
    """Configuration for output formatting and structure."""
    
    format: OutputFormat = Field(OutputFormat.STRUCTURED_JSON, description="Output format")
    chunk_strategy: ChunkStrategy = Field(ChunkStrategy.SEMANTIC_HEADERS, description="Content chunking strategy")
    preserve_spatial_info: bool = Field(True, description="Include spatial positioning data")
    include_metadata: bool = Field(True, description="Include extraction metadata")
    
    # Format-specific settings
    markdown_headers: bool = Field(True, description="Use markdown header syntax (# ## ###)")
    json_indent: int = Field(2, ge=0, le=8, description="JSON indentation spaces")
    include_page_breaks: bool = Field(False, description="Mark page boundaries in output")
    
    # Chunking settings
    chunk_size: Optional[int] = Field(None, ge=100, description="Target chunk size in characters")
    chunk_overlap: int = Field(0, ge=0, description="Character overlap between chunks")
    min_chunk_size: int = Field(50, ge=10, description="Minimum chunk size")


class ExtractionProfile(BaseModel):
    """Main configuration profile for PDF extraction."""
    
    name: str = Field(..., min_length=1, description="Profile name")
    pdf_family: str = Field(..., min_length=1, description="PDF family identifier")
    version: str = Field("1.0", description="Configuration version")
    description: Optional[str] = Field(None, description="Profile description")
    
    # Core configuration sections
    document_analysis: DocumentAnalysis = Field(default_factory=DocumentAnalysis)
    header_rules: HeaderRules = Field(default_factory=HeaderRules)
    special_elements: SpecialElements = Field(default_factory=SpecialElements)
    content_filters: ContentFilters = Field(default_factory=ContentFilters)
    output_settings: OutputSettings = Field(default_factory=OutputSettings)
    
    # Optional metadata
    author: Optional[str] = Field(None, description="Configuration author")
    created_date: Optional[str] = Field(None, description="Creation date")
    notes: List[str] = Field(default_factory=list, description="Configuration notes")
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Don't allow extra fields
        validate_assignment = True  # Validate on assignment
        
    def model_dump_yaml(self) -> str:
        """Export configuration as YAML string."""
        import yaml
        from enum import Enum
        
        def enum_representer(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data.value)
        
        yaml.add_representer(ReadingOrder, enum_representer)
        yaml.add_representer(OutputFormat, enum_representer)
        yaml.add_representer(ChunkStrategy, enum_representer)
        yaml.add_representer(TableDetectionMethod, enum_representer)
        yaml.add_representer(SpecialElementAction, enum_representer)
        
        data = self.model_dump(exclude_none=True, mode='json')
        return yaml.dump(data, default_flow_style=False, indent=2)
    
    def save_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        from pathlib import Path
        Path(path).write_text(self.model_dump_yaml(), encoding='utf-8')
    
    @classmethod
    def from_yaml(cls, path: str) -> 'ExtractionProfile':
        """Load configuration from YAML file."""
        import yaml
        from pathlib import Path
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_json(cls, path: str) -> 'ExtractionProfile':
        """Load configuration from JSON file."""
        import json
        from pathlib import Path
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)


class ConfigurationValidator:
    """Utility class for validating extraction configurations."""
    
    @staticmethod
    def validate_config_file(config_path: str) -> tuple[bool, Union[ExtractionProfile, str]]:
        """
        Validate a configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple of (is_valid, config_or_error_message)
        """
        from pathlib import Path
        
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                return False, f"Configuration file not found: {config_path}"
            
            if config_path.suffix.lower() in ['.yml', '.yaml']:
                config = ExtractionProfile.from_yaml(str(config_path))
            elif config_path.suffix.lower() == '.json':
                config = ExtractionProfile.from_json(str(config_path))
            else:
                return False, f"Unsupported configuration format: {config_path.suffix}"
            
            return True, config
            
        except Exception as e:
            return False, f"Configuration validation failed: {str(e)}"
    
    @staticmethod
    def create_example_config() -> ExtractionProfile:
        """Create an example configuration for documentation."""
        return ExtractionProfile(
            name="Dolmenwood Player's Book",
            pdf_family="dolmenwood_core",
            version="1.0",
            description="Configuration for extracting Dolmenwood Player's Book content",
            author="Example User",
            document_analysis=DocumentAnalysis(
                body_text_size=11.0,
                column_detection=True
            ),
            header_rules=HeaderRules(
                level_1=[
                    HeaderRule(
                        color="#d2691e",  # Orange
                        size_min=18.0,
                        size_max=24.0,
                        bold=True,
                        context_patterns=[r"^[A-Z]{3,}$"],  # ALL CAPS
                        description="Primary class headers in orange"
                    )
                ],
                level_2=[
                    HeaderRule(
                        color="#8b4513",  # Brown
                        size_min=14.0,
                        size_max=17.0,
                        bold=True,
                        description="Section headers in brown"
                    )
                ]
            ),
            special_elements=SpecialElements(
                illuminated_letters=IlluminatedLetters(
                    enabled=True,
                    size_threshold=20.0,
                    action=SpecialElementAction.IGNORE
                ),
                stat_blocks=StatBlocks(
                    enabled=True,
                    patterns=[
                        r"^(STR|DEX|CON|INT|WIS|CHA):\s*\d+",
                        r"^(AC|HD|HP):\s*[\d+/-]+"
                    ]
                )
            ),
            notes=[
                "Based on analysis of pages 75-78",
                "Orange headers are character classes",
                "Brown headers are skill sections"
            ]
        )


# Example usage and testing
if __name__ == "__main__":
    # Create and validate example configuration
    example_config = ConfigurationValidator.create_example_config()
    
    # Save as YAML
    example_config.save_yaml("example_config.yml")
    
    # Validate the saved file
    is_valid, result = ConfigurationValidator.validate_config_file("example_config.yml")
    
    if is_valid:
        print("✅ Configuration is valid!")
        print(f"Profile: {result.name}")
        print(f"PDF Family: {result.pdf_family}")
        print(f"Header rules defined: {len(result.header_rules.level_1)} L1, {len(result.header_rules.level_2)} L2")
    else:
        print(f"❌ Configuration validation failed: {result}")