#!/usr/bin/env python3
"""
University Recommendation System Initialization Script
Sets up the complete system with data generation, indexing, and testing
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if all required packages are installed"""
    logger.info("Checking requirements...")
    
    try:
        import pandas
        import numpy
        import streamlit
        import plotly
        import qdrant_client
        import sentence_transformers
        import crewai
        import openai
        logger.info(" All required packages are installed")
        return True
    except ImportError as e:
        logger.error(f" Missing package: {e}")
        logger.info("Please run: pip install -r requirements.txt")
        return False

def create_directories():
    """Create necessary directories"""
    logger.info("Creating directories...")
    
    directories = [
        "data/raw",
        "data/processed", 
        "data/processed/embeddings",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def generate_sample_data():
    """Generate sample university data"""
    logger.info("Generating sample data...")
    
    try:
        # Ensure data/raw directory exists
        Path("data/raw").mkdir(parents=True, exist_ok=True)
        
        from generate_sample_data import generate_sample_data
        df = generate_sample_data()
        
        # Verify file was created
        csv_path = Path("data/raw/universities_sample.csv")
        if csv_path.exists() and csv_path.stat().st_size > 0:
            logger.info(f"✅ Generated {len(df)} university records")
            logger.info(f"   File saved to: {csv_path.absolute()}")
            return True
        else:
            logger.error(f"❌ CSV file was not created or is empty: {csv_path}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to generate sample data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def setup_qdrant():
    """Setup Qdrant vector database"""
    logger.info("Setting up Qdrant...")
    
    try:
        from src.database.qdrant_client import UniversityVectorDB
        
        # Initialize database
        logger.info("   Connecting to Qdrant...")
        db = UniversityVectorDB()
        
        logger.info("   Creating collection...")
        db.create_collection()
        logger.info("✅ Qdrant collection created")
        
        # Load and index data - use relative path, load_universities will handle it
        csv_path = "data/raw/universities_sample.csv"
        csv_file = Path(csv_path)
        
        if not csv_file.exists():
            # Try absolute path
            csv_file = Path(os.getcwd()) / csv_path
            if not csv_file.exists():
                logger.error(f"❌ CSV file not found: {csv_path}")
                logger.error(f"   Tried: {Path(csv_path).absolute()}")
                logger.error(f"   Tried: {csv_file.absolute()}")
                logger.error("   Please run generate_sample_data() first")
                return False
        
        logger.info(f"   Loading data from: {csv_file.absolute()}")
        success = db.load_universities(str(csv_file))
        
        if success:
            logger.info("✅ Data indexed successfully")
            return True
        else:
            logger.error("❌ Failed to index data")
            return False
            
    except ConnectionError as e:
        logger.error(f"❌ Failed to connect to Qdrant: {e}")
        logger.error("   Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to setup Qdrant: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_system():
    """Test the complete system"""
    logger.info("Testing system...")
    
    try:
        from src.database.qdrant_client import UniversityVectorDB
        from src.utils.ranking import UniversityRanker
        
        # Test database connection
        db = UniversityVectorDB()
        
        # First test without filters
        results = db.search_universities(
            query="Computer Science",
            filters=None,
            limit=5
        )
        
        if results:
            logger.info(f"✅ Found {len(results)} test results (without filters)")
            
            # Test with filters (less restrictive)
            results_filtered = db.search_universities(
                query="Computer Science",
                filters={'countries': ['USA', 'UK']},
                limit=5
            )
            
            if results_filtered:
                logger.info(f"✅ Found {len(results_filtered)} test results (with country filter)")
            else:
                logger.warning("⚠️  No results with country filter (this is OK if data doesn't match)")
            
            # Continue with ranking test using unfiltered results
            
            # Test ranking
            ranker = UniversityRanker()
            test_profile = {
                'gpa': 3.5,
                'budget': 40000,
                'work_experience': 'Software engineer for 2 years'
            }
            
            ranked = ranker.rank_universities(results, test_profile)
            logger.info(f" Ranking system working - top score: {ranked[0]['final_score']:.3f}")
            
            return True
        else:
            logger.error(" No search results found")
            return False
            
    except Exception as e:
        logger.error(f" System test failed: {e}")
        return False

def main():
    """Main initialization function"""
    logger.info("="*60)
    logger.info(" UNIVERSITY RECOMMENDATION SYSTEM INITIALIZATION")
    logger.info("="*60)
    
    # Step 1: Check requirements
    if not check_requirements():
        logger.error("Please install requirements first: pip install -r requirements.txt")
        return False
    
    # Step 2: Create directories
    create_directories()
    
    # Step 3: Generate sample data
    if not generate_sample_data():
        logger.error("Failed to generate sample data")
        return False
    
    # Step 4: Setup Qdrant
    if not setup_qdrant():
        logger.error("Failed to setup Qdrant")
        return False
    
    # Step 5: Test system
    if not test_system():
        logger.error("System test failed")
        return False
    
    logger.info("="*60)
    logger.info(" SYSTEM INITIALIZATION COMPLETE!")
    logger.info("="*60)
    logger.info("To start the application:")
    logger.info("  streamlit run app/streamlit_app.py")
    logger.info("="*60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
