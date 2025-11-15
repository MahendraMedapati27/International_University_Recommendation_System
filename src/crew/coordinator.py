from crewai import Crew, Process
from src.agents.researcher import ResearcherAgent
from src.agents.matcher import MatcherAgent
from src.agents.counselor import CounselorAgent
from src.agents.verifier import VerifierAgent
from typing import Dict
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


class UniversityRecommendationPipeline:
    """University Recommendation Pipeline - matches article structure"""
    
    def __init__(self, db, llm):
        """Initialize pipeline with database and LLM"""
        self.db = db
        self.llm = llm
        
        # Initialize agents
        self.researcher = ResearcherAgent(llm)
        self.matcher = MatcherAgent(llm, db)
        self.counselor = CounselorAgent(llm)
        self.verifier = VerifierAgent(llm)

    def run(self, student_profile: Dict) -> Dict:
        """Run the complete recommendation pipeline - matches article structure"""
        try:
            # Step 1: Research enrichment
            research = self.researcher.run_researcher(student_profile)
            
            # Step 2: Match universities using Qdrant
            matches = self.matcher.run_matcher(student_profile, research)
            
            # Step 3: Create application plan
            plan = self.counselor.create_plan(matches, student_profile)
            
            # Step 4: Verify deadlines
            issues = self.verifier.verify_deadlines(matches) if matches else []
            
            return {
                "profile": student_profile,
                "research": research,
                "matches": matches if matches else [],
                "plan": plan,
                "issues": issues
            }
        except Exception as e:
            import logging
            logging.error(f"Pipeline error: {e}")
            # Return empty result on error
            return {
                "profile": student_profile,
                "research": {},
                "matches": [],
                "plan": "Error generating plan. Please try again.",
                "issues": []
            }


class UniversityRecommendationCrew:
    """CrewAI-based recommendation system - maintains compatibility"""
    
    def __init__(self, vector_db):
        """Initialize the crew with all agents"""
        
        # Get LLM configuration for Groq
        from src.utils.groq_llm import create_groq_llm
        
        # Initialize Groq LLM
        self.groq_llm = create_groq_llm(
            model='llama-3.1-8b-instant',  # or 'llama-3.3-70b-versatile' for better performance
            temperature=0.7
        )

        # Initialize agents with Groq LLM
        self.researcher = ResearcherAgent(self.groq_llm)
        self.matcher = MatcherAgent(self.groq_llm, vector_db)
        self.counselor = CounselorAgent(self.groq_llm)
        self.verifier = VerifierAgent(self.groq_llm)

        self.vector_db = vector_db
        
        # Also create pipeline instance
        self.pipeline = UniversityRecommendationPipeline(vector_db, self.groq_llm)

    def run_recommendation_process(self, student_profile: Dict) -> Dict:
        """Run the complete recommendation process"""
        
        print("\n" + "="*60)
        print("🎓 UNIVERSITY RECOMMENDATION SYSTEM")
        print("="*60 + "\n")
        
        # Use pipeline approach - matches article
        result = self.pipeline.run(student_profile)
        
        print("\n" + "="*60)
        print("✅ RECOMMENDATIONS COMPLETE")
        print("="*60 + "\n")
        
        return {
            'recommendations': result,
            'profile': student_profile,
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    from src.database.qdrant_client import UniversityVectorDB
    
    # Initialize
    db = UniversityVectorDB()
    crew = UniversityRecommendationCrew(db)
    
    # Test profile
    test_profile = {
        'name': 'Priya Sharma',
        'origin_country': 'India',
        'target_countries': ['UK', 'Canada', 'Germany'],
        'program': 'Computer Science',
        'level': 'masters',
        'budget': 30000,
        'gpa': 3.6,
        'interests': ['AI', 'Machine Learning', 'Data Science'],
        'career_goals': 'Research scientist at tech company or PhD',
        'work_experience': '2 years as software engineer'
    }
    
    results = crew.run_recommendation_process(test_profile)
    print(results)