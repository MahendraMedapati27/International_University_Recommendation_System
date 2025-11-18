"""Fix Qdrant collection by recreating it with correct configuration"""
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.qdrant_client import UniversityVectorDB

def main():
    print("=" * 60)
    print("🔧 Fixing Qdrant Collection")
    print("=" * 60)
    
    try:
        db = UniversityVectorDB()
        
        # Check if collection exists
        if db.client.collection_exists(db.collection_name):
            print(f"\n⚠️  Collection '{db.collection_name}' exists but may be misconfigured.")
            response = input("Delete and recreate? (y/n): ")
            if response.lower() == 'y':
                print(f"\n🗑️  Deleting collection '{db.collection_name}'...")
                db.client.delete_collection(db.collection_name)
                print("✅ Collection deleted.")
            else:
                print("❌ Aborted.")
                return
        
        # Create collection with correct configuration
        print(f"\n📦 Creating collection '{db.collection_name}' with vector size {db.vector_size}...")
        db.create_collection()
        
        # Load data
        csv_path = "data/raw/universities_sample.csv"
        if os.path.exists(csv_path):
            print(f"\n📥 Loading data from {csv_path}...")
            success = db.load_universities(csv_path)
            if success:
                print("\n✅ Collection fixed and data loaded successfully!")
            else:
                print("\n❌ Failed to load data. Check logs for details.")
                return
        else:
            print(f"\n⚠️  CSV file not found: {csv_path}")
            print("✅ Collection created, but no data loaded.")
        
        # Verify
        if db.verify_collection():
            collection_info = db.client.get_collection(db.collection_name)
            print(f"\n✅ Verification successful!")
            print(f"   - Collection: {db.collection_name}")
            print(f"   - Vector size: {db.vector_size}")
            print(f"   - Points indexed: {collection_info.points_count}")
        else:
            print("\n❌ Verification failed!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

