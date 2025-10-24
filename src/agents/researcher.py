from crewai import Agent, Task
from typing import Dict
import json


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
        """Create task to enrich student profile with contextual requirements"""
        return Task(
            description=f"""
Analyze this student profile and add important contextual information:

Student Profile:
- Origin Country: {student_profile.get('origin_country', 'Not specified')}
- Target Countries: {', '.join(student_profile.get('target_countries', []))}
- Budget: ${student_profile.get('budget', 'Not specified')}
- Level: {student_profile.get('level', 'Not specified')}

Please provide:
1. Visa requirements for each target country
2. Language test requirements (IELTS, TOEFL, etc.)
3. Typical processing times
4. Any country-specific considerations
5. Cost of living estimates

Format as structured JSON.
""",
            agent=self.agent,
            expected_output="JSON with enriched country and visa information"
        )
