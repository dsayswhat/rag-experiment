"""
Core configuration management
Used by database scripts and MCP server
"""

import os
from typing import Optional
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent


def load_env_file(env_path: Optional[Path] = None) -> None:
    """Load environment variables from .env file"""
    if env_path is None:
        # Look for .env in project root
        env_path = get_project_root() / ".env"
    
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value


class Config:
    """Centralized configuration class"""
    
    def __init__(self, env_path: Optional[Path] = None):
        # Load .env file if it exists
        load_env_file(env_path)
        
        # Database configuration
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://username:password@localhost/content_db"
        )
        
        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Set it in your environment or in a .env file."
            )
        
        # Embedding configuration
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        self.embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        
        # Database performance settings
        self.default_batch_size = int(os.getenv("DEFAULT_BATCH_SIZE", "20"))
        self.max_chunk_size = int(os.getenv("MAX_CHUNK_SIZE", "32000"))
        
        # MCP server settings
        self.mcp_server_name = os.getenv("MCP_SERVER_NAME", "content-server")
        self.mcp_server_version = os.getenv("MCP_SERVER_VERSION", "1.0.0")
        self.default_search_limit = int(os.getenv("DEFAULT_SEARCH_LIMIT", "5"))
        self.max_search_limit = int(os.getenv("MAX_SEARCH_LIMIT", "20"))
        
        # Content domain configuration
        self.content_domain = os.getenv("CONTENT_DOMAIN", "documents")
        self.default_source_type = os.getenv("DEFAULT_SOURCE_TYPE", "official")
        
        # Default content types (can be overridden by environment)
        default_types = "reference,procedure,concept,example"
        content_types_str = os.getenv("CONTENT_TYPES", default_types)
        self.content_types = [t.strip() for t in content_types_str.split(",") if t.strip()]
    
    def validate(self) -> None:
        """Validate configuration"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        if not self.database_url:
            raise ValueError("Database URL is required")
    
    def __repr__(self) -> str:
        return f"Config(database_url='{self.database_url[:50]}...', embedding_model='{self.embedding_model}')"


# Global config instance
_config = None


def get_config(env_path: Optional[Path] = None) -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = Config(env_path)
        _config.validate()
    return _config


def reset_config() -> None:
    """Reset the global configuration (useful for testing)"""
    global _config
    _config = None