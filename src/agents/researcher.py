from crewai import Agent, Task
from typing import Dict
import json


# Researcher Agent Template - matches article structure
RESEARCHER_TMPL = """
Student from {origin} applying for {level} programs in {countries}.
Provide JSON for each country:
- Visa type, processing time, financial proof
- Language requirements
- Application timeline
- Average cost of living
"""


class ResearcherAgent:
    def __init__(self, llm):
        self.agent = Agent(
            role="University Research Specialist",
            goal="Gather and enrich university data with visa requirements, language prerequisites, and regional considerations",
            backstory="""You are an expert in international education with deep knowledge of 
            visa requirements, language tests, and regional higher education systems. You help 
            students understand country-specific requirements and prepare documentation.""",
            llm=llm,
            verbose=True,
            allow_delegation=False
        )

    def create_enrichment_task(self, student_profile: Dict) -> Task:
        """Create task to enrich student profile with contextual requirements - matches article"""
        origin = student_profile.get('origin_country', 'Not specified')
        level = student_profile.get('level', 'Not specified')
        countries = ', '.join(student_profile.get('target_countries', []))
        
        # Use article's template structure
        description = RESEARCHER_TMPL.format(
            origin=origin,
            level=level,
            countries=countries
        )
        
        return Task(
            description=description,
            agent=self.agent,
            expected_output="JSON with enriched country and visa information"
        )
    
    def run_researcher(self, student_profile: Dict) -> Dict:
        """Run researcher agent and return enriched data - matches article"""
        task = self.create_enrichment_task(student_profile)
        # In actual implementation, this would execute the task via CrewAI
        # For now, return a structured response
        return {
            "origin": student_profile.get('origin_country', 'Not specified'),
            "level": student_profile.get('level', 'Not specified'),
            "countries": student_profile.get('target_countries', [])
        }
