"""
Core OpenAI utilities for content processing
"""

import openai
from typing import List, Union
from .config import get_config


def get_openai_client():
    """Get configured OpenAI client"""
    config = get_config()
    return openai.OpenAI(api_key=config.openai_api_key)


async def get_embedding_async(text: str) -> List[float]:
    """Generate embedding for text using OpenAI (async)"""
    config = get_config()
    client = get_openai_client()
    
    try:
        response = client.embeddings.create(
            model=config.embedding_model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"Failed to generate embedding: {str(e)}")


def get_embedding_sync(text: str) -> List[float]:
    """Generate embedding for text using OpenAI (sync)"""
    config = get_config()
    client = get_openai_client()
    
    try:
        response = client.embeddings.create(
            model=config.embedding_model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"Failed to generate embedding: {str(e)}")


def get_embeddings_batch_sync(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts in a single API call (sync)"""
    config = get_config()
    client = get_openai_client()
    
    try:
        response = client.embeddings.create(
            model=config.embedding_model,
            input=texts
        )
        return [embedding.embedding for embedding in response.data]
    except Exception as e:
        raise Exception(f"Failed to generate batch embeddings: {str(e)}")


def average_embeddings(embeddings: List[List[float]]) -> List[float]:
    """Average multiple embeddings into a single embedding"""
    if not embeddings:
        raise ValueError("Cannot average empty embeddings list")
    
    if len(embeddings) == 1:
        return embeddings[0]
    
    # Get dimensions from first embedding
    dimensions = len(embeddings[0])
    
    # Initialize averaged embedding
    averaged = [0.0] * dimensions
    
    # Sum all embeddings
    for embedding in embeddings:
        if len(embedding) != dimensions:
            raise ValueError("All embeddings must have the same dimensions")
        for i, value in enumerate(embedding):
            averaged[i] += value
    
    # Divide by count to get average
    count = len(embeddings)
    averaged = [value / count for value in averaged]
    
    return averaged