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


class UniversityRecommendationCrew:
    def __init__(self, vector_db):
        """Initialize the crew with all agents"""
        
        # Get LLM configuration for Groq
        from ..utils.groq_llm import create_groq_llm
        
        # Initialize Groq LLM
        groq_llm = create_groq_llm(
            model='llama-3.1-8b-instant',  # or 'llama-3.3-70b-versatile' for better performance
            temperature=0.7
        )

        # Initialize agents with Groq LLM
        self.researcher = ResearcherAgent(groq_llm)
        self.matcher = MatcherAgent(groq_llm, vector_db)
        self.counselor = CounselorAgent(groq_llm)
        self.verifier = VerifierAgent(groq_llm)

        self.vector_db = vector_db

    def run_recommendation_process(self, student_profile: Dict) -> Dict:
        """Run the complete recommendation process"""
        
        print("\n" + "="*60)
        print("🎓 UNIVERSITY RECOMMENDATION SYSTEM")
        print("="*60 + "\n")
        
        # Step 1: Research enrichment
        print("📚 Step 1: Researching requirements and context…")
        enrichment_task = self.researcher.create_enrichment_task(student_profile)
        
        # Step 2: Match universities
        print("🔍 Step 2: Finding matching universities…")
        enriched_data = {} # Would be populated by researcher task
        matching_task = self.matcher.create_matching_task(student_profile, enriched_data)
        
        # Step 3: Generate advice
        print("💡 Step 3: Generating personalized advice…")
        advisory_task = self.counselor.create_advisory_task(
            student_profile, 
            "matched_universities" # Would be populated by matcher
        )
        
        # Step 4: Verify information
        print("✓ Step 4: Verifying critical information…")
        verification_task = self.verifier.create_verification_task({})
        
        # Create crew with sequential process
        crew = Crew(
            agents=[
                self.researcher.agent,
                self.matcher.agent,
                self.counselor.agent,
                self.verifier.agent
            ],
            tasks=[
                enrichment_task,
                matching_task,
                advisory_task,
                verification_task
            ],
            process=Process.sequential,
            verbose=True,
            llm=groq_llm  # Explicitly set the LLM to use Groq
        )
        
        # Execute
        result = crew.kickoff()
        
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