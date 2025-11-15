"""Test Qdrant connection"""
from src.database.qdrant_client import UniversityVectorDB

try:
    db = UniversityVectorDB()
    print("✅ Qdrant connection successful!")
    
    # Check if collection exists
    exists = db.client.collection_exists("universities")
    print(f"📊 Collection 'universities' exists: {exists}")
    
    if exists:
        collection_info = db.client.get_collection("universities")
        print(f"📈 Universities indexed: {collection_info.points_count}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")

