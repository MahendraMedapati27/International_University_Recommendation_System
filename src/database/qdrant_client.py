from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, Range, MatchValue, MatchAny
)
from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class UniversityVectorDB:
    def __init__(self):
        """Initialize Qdrant client and embedding model"""
        try:
            self.client = QdrantClient(
                host=os.getenv('QDRANT_HOST', 'localhost'),
                port=int(os.getenv('QDRANT_PORT', 6333)),
                timeout=10  # Add timeout for connection
            )
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Could not connect to Qdrant at {os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', 6333)}. Make sure Qdrant is running.")

        # Use a good sentence transformer model
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.vector_size = 384  # Dimension for all-MiniLM-L6-v2

        self.collection_name = "universities"
    
    def verify_collection(self) -> bool:
        """Verify collection exists and has correct configuration"""
        try:
            if not self.client.collection_exists(self.collection_name):
                return False
            
            collection_info = self.client.get_collection(self.collection_name)
            # Check if vector size matches
            if hasattr(collection_info.config, 'params') and hasattr(collection_info.config.params, 'vectors'):
                vector_size = collection_info.config.params.vectors.size
                if vector_size != self.vector_size:
                    logger.warning(f"Collection vector size mismatch: {vector_size} != {self.vector_size}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error verifying collection: {e}")
            return False

    def create_collection(self):
        """Create Qdrant collection for universities - matches article structure"""
        try:
            # Check if collection exists first
            if self.client.collection_exists(self.collection_name):
                print(f"⚠️ Collection '{self.collection_name}' already exists. Recreating...")
                self.client.delete_collection(self.collection_name)
            
            # Create collection with correct vector configuration
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"✅ Collection '{self.collection_name}' created successfully with vector size {self.vector_size}")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise e

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        embedding = self.encoder.encode(text)
        return embedding.tolist()

    def prepare_search_text(self, row: pd.Series) -> str:
        """Prepare comprehensive search text from university data - matches article structure"""
        # Match article's format: "univ_name | program | description"
        return f"{row['univ_name']} | {row['program']} | {row['description']}"

    def load_universities(self, csv_path: str):
        """Load universities from CSV and index in Qdrant - matches article structure"""
        df = pd.read_csv(csv_path)

        print(f"📥 Loading {len(df)} university programs...")

        points = []
        for idx, row in df.iterrows():
            try:
                # Create search text - matches article format
                text = f"{row['univ_name']} | {row['program']} | {row['description']}"
                
                # Generate embedding
                vector = self.encoder.encode(text).tolist()
                
                # Validate vector dimension
                if len(vector) != self.vector_size:
                    logger.error(f"Vector dimension mismatch at index {idx}: expected {self.vector_size}, got {len(vector)}")
                    continue

                # Prepare payload - ensure proper data types
                payload = {}
                for col in df.columns:
                    value = row[col]
                    # Convert pandas types to Python native types
                    if pd.isna(value):
                        payload[col] = None
                    elif isinstance(value, (pd.Int64Dtype, pd.Int32Dtype)):
                        payload[col] = int(value) if not pd.isna(value) else None
                    elif isinstance(value, (pd.Float64Dtype, pd.Float32Dtype)):
                        payload[col] = float(value) if not pd.isna(value) else None
                    elif isinstance(value, pd.Timestamp):
                        payload[col] = str(value)
                    else:
                        payload[col] = str(value) if value is not None else None
                
                payload['search_text'] = text

                point = PointStruct(
                    id=int(idx),  # Ensure ID is int
                    vector=vector,
                    payload=payload
                )
                points.append(point)

                if (idx + 1) % 50 == 0:
                    print(f"📦 Processed {idx + 1}/{len(df)} programs")
                    
            except Exception as e:
                logger.warning(f"Error processing row {idx}: {e}")
                continue

        if not points:
            raise ValueError("No valid points to index. Check your data file.")

        # Upload to Qdrant in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            print(f"📤 Uploaded batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")

        print(f"✅ Successfully indexed {len(points)} programs in Qdrant")

    def search_universities(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Search for universities with optional filters - matches article structure"""
        try:
            # Check if collection exists
            if not self.client.collection_exists(self.collection_name):
                logger.error(f"Collection '{self.collection_name}' does not exist")
                raise ValueError(f"Collection '{self.collection_name}' does not exist. Please initialize the database first.")
            
            # Generate query embedding - matches article
            qvec = self.encoder.encode(query).tolist()
            
            # Validate vector dimension
            if len(qvec) != self.vector_size:
                logger.error(f"Vector dimension mismatch: expected {self.vector_size}, got {len(qvec)}")
                raise ValueError(f"Vector dimension mismatch: expected {self.vector_size}, got {len(qvec)}")
            
            # Build Qdrant filter if provided - matches article structure
            must = []
            if filters and filters.get("countries"):
                countries = filters["countries"]
                if isinstance(countries, list) and len(countries) > 0:
                    # Normalize country names (handle variations)
                    normalized_countries = [c.strip() for c in countries]
                    must.append(
                        FieldCondition(
                            key="country",
                            match=MatchAny(any=normalized_countries)
                        )
                    )
                    logger.info(f"Applied country filter: {normalized_countries}")
            
            if filters and filters.get("max_tuition"):
                max_tuition = filters["max_tuition"]
                if max_tuition and isinstance(max_tuition, (int, float)) and max_tuition > 0:
                    # Add 20% buffer to account for scholarships and variations
                    max_tuition_with_buffer = int(max_tuition * 1.2)
                    must.append(
                        FieldCondition(
                            key="tuition_usd",
                            range=Range(lte=max_tuition_with_buffer)
                        )
                    )
                    logger.info(f"Applied tuition filter: <= ${max_tuition_with_buffer} (original: ${max_tuition})")
            
            if filters and filters.get("level"):
                level = filters["level"]
                if level and isinstance(level, str):
                    # Make level matching case-insensitive by normalizing
                    level_normalized = level.lower().strip()
                    must.append(
                        FieldCondition(
                            key="level",
                            match=MatchValue(value=level_normalized)
                        )
                    )
                    logger.info(f"Applied level filter: {level_normalized}")
            
            query_filter = Filter(must=must) if must else None
            
            # Perform search - matches article
            # Note: with_payload is True by default, so we don't need to specify it
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=qvec,
                query_filter=query_filter,
                limit=limit
            )
            
            # Format results - matches article format
            formatted_results = []
            for r in results:
                try:
                    # Ensure payload is a dict and add similarity score
                    payload = dict(r.payload) if r.payload else {}
                    payload['similarity_score'] = float(r.score)
                    formatted_results.append(payload)
                except Exception as e:
                    logger.warning(f"Error formatting result: {e}")
                    continue
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            # Return empty list on error rather than crashing
            return []


if __name__ == "__main__":
    # Test the database
    db = UniversityVectorDB()
    db.create_collection()
    db.load_universities('data/raw/universities_sample.csv')

    # Test search
    results = db.search_universities(
        query="Computer Science programs with strong research in AI and machine learning",
        filters={'countries': ['USA', 'UK'], 'max_tuition': 40000},
        limit=5
    )

    print("\nTop 5 Results:")
    for i, uni in enumerate(results, 1):
        print(f"{i}. {uni['univ_name']} - {uni['program']} ({uni['country']})")
        print(f"   Similarity: {uni['similarity_score']:.3f}, Tuition: ${uni['tuition_usd']:,}")
