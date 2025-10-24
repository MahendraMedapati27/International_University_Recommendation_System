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
        self.client = QdrantClient(
            host=os.getenv('QDRANT_HOST', 'localhost'),
            port=int(os.getenv('QDRANT_PORT', 6333))
        )

        # Use a good sentence transformer model
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.vector_size = 384  # Dimension for all-MiniLM-L6-v2

        self.collection_name = "universities"

    def create_collection(self):
        """Create Qdrant collection for universities"""
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"✅ Collection '{self.collection_name}' created successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"⚠️ Collection '{self.collection_name}' already exists")
            else:
                raise e

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        embedding = self.encoder.encode(text)
        return embedding.tolist()

    def prepare_search_text(self, row: pd.Series) -> str:
        """Prepare comprehensive search text from university data"""
        parts = [
            f"University: {row['univ_name']}",
            f"Program: {row['program']} ({row['level']})",
            f"Country: {row['country']}",
            f"Language: {row['language']}",
            f"Description: {row['description'][:500]}",
            f"Tuition: ${row['tuition_usd']}",
            f"Research: {row['research_output']}",
            f"Scholarships: {row['scholarship_tags']}"
        ]
        return " | ".join(parts)

    def load_universities(self, csv_path: str):
        """Load universities from CSV and index in Qdrant"""
        df = pd.read_csv(csv_path)

        print(f"📥 Loading {len(df)} university programs...")

        points = []
        for idx, row in df.iterrows():
            # Create search text
            search_text = self.prepare_search_text(row)

            # Generate embedding
            vector = self.generate_embedding(search_text)

            # Prepare payload
            payload = {
                'univ_id': row['univ_id'],
                'univ_name': row['univ_name'],
                'country': row['country'],
                'program': row['program'],
                'level': row['level'],
                'tuition_usd': int(row['tuition_usd']),
                'deadline': row['deadline'],
                'language': row['language'],
                'acceptance_rate': float(row['acceptance_rate']),
                'scholarship_tags': row['scholarship_tags'],
                'description': row['description'],
                'qs_ranking': int(row['qs_ranking']) if pd.notna(row['qs_ranking']) else None,
                'research_output': row['research_output'],
                'living_cost_monthly': int(row['living_cost_monthly']),
                'visa_difficulty': row['visa_difficulty'],
                'avg_class_size': int(row['avg_class_size']),
                'employment_rate_6mo': float(row['employment_rate_6mo']),
                'search_text': search_text
            }

            point = PointStruct(
                id=idx,
                vector=vector,
                payload=payload
            )
            points.append(point)

            if (idx + 1) % 50 == 0:
                print(f"📦 Processed {idx + 1}/{len(df)} programs")

        # Upload to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"✅ Successfully indexed {len(points)} programs in Qdrant")

    def search_universities(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Search for universities with optional filters"""
        # Generate query embedding
        query_vector = self.generate_embedding(query)

        # Build Qdrant filter if provided
        qdrant_filter = None
        if filters:
            must_conditions = []

            if 'countries' in filters and filters['countries']:
                must_conditions.append(
                    FieldCondition(
                        key="country",
                        match=MatchAny(any=filters['countries'])
                    )
                )

            if 'max_tuition' in filters:
                must_conditions.append(
                    FieldCondition(
                        key="tuition_usd",
                        range=Range(lte=filters['max_tuition'])
                    )
                )

            if 'min_tuition' in filters:
                must_conditions.append(
                    FieldCondition(
                        key="tuition_usd",
                        range=Range(gte=filters['min_tuition'])
                    )
                )

            if 'level' in filters:
                must_conditions.append(
                    FieldCondition(
                        key="level",
                        match=MatchValue(value=filters['level'])
                    )
                )

            if 'language' in filters:
                must_conditions.append(
                    FieldCondition(
                        key="language",
                        match=MatchValue(value=filters['language'])
                    )
                )

            if must_conditions:
                qdrant_filter = Filter(must=must_conditions)

        # Perform search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=limit
        )

        # Format results
        universities = []
        for result in results:
            uni = result.payload.copy()
            uni['similarity_score'] = result.score
            universities.append(uni)

        return universities


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
