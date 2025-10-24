"""
Database module for university recommendation system
Handles Qdrant vector database operations and data loading
"""

from .qdrant_client import UniversityVectorDB

__all__ = [
    'UniversityVectorDB'
]
