from crewai import Agent, Task
from typing import Dict, List
import json


class MatcherAgent:
    def __init__(self, llm, vector_db):
        self.vector_db = vector_db
        self.agent = Agent(
            role="University Matching Specialist",
            goal="Find the best-fit universities based on student profile and preferences using semantic search",
            backstory="""You are a data-driven matching expert who uses advanced vector search 
            to find universities that truly align with student goals, not just superficial criteria. 
            You understand that fit goes beyond rankings.""",
            llm=llm,
            verbose=True,
            allow_delegation=False
        )

    def create_matching_task(self, student_profile: Dict, enriched_data: Dict) -> Task:
        """Create task to match student with universities"""

        # Build search query from profile
        query_parts = []
        if 'interests' in student_profile:
            query_parts.append(f"Research interests: {', '.join(student_profile['interests'])}")
        if 'program' in student_profile:
            query_parts.append(f"Program: {student_profile['program']}")
        if 'career_goals' in student_profile:
            query_parts.append(f"Career goals: {student_profile['career_goals']}")

        search_query = " | ".join(query_parts)

        # Build filters
        filters = {}
        if 'target_countries' in student_profile:
            filters['countries'] = student_profile['target_countries']
        if 'budget' in student_profile:
            filters['max_tuition'] = student_profile['budget']
        if 'level' in student_profile:
            filters['level'] = student_profile['level']

        # Search vector database
        results = self.vector_db.search_universities(
            query=search_query,
            filters=filters,
            limit=20
        )

        return Task(
            description=f"""
Based on vector search results, analyze and rank these {len(results)} universities
for the student profile.

Consider:
1. Semantic similarity score
2. Acceptance rate vs student qualifications
3. Research alignment
4. Budget fit
5. Career prospects

Provide top 10 recommendations categorized as:
- Reach (3 universities)
- Target (4 universities)
- Safety (3 universities)

For each, explain WHY it's a good fit.

Search Results:
{self._format_results(results)}
""",
            agent=self.agent,
            expected_output="Categorized list of universities with fit explanations"
        )

    def _format_results(self, results: List[Dict]) -> str:
        """Format search results for the agent"""
        formatted = []
        for i, uni in enumerate(results, 1):
            formatted.append(f"""
{i}. {uni['univ_name']} - {uni['program']}
Country: {uni['country']}
Tuition: ${uni['tuition_usd']:,}
Acceptance Rate: {uni['acceptance_rate'] * 100:.1f}%
Similarity Score: {uni['similarity_score']:.3f}
Research: {uni['research_output']}
Employment Rate: {uni['employment_rate_6mo'] * 100:.1f}%
""")
        return "\n".join(formatted)
