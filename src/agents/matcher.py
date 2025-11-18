from crewai import Agent, Task
from typing import Dict, List
import json
import logging


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

    def run_matcher(self, student_profile: Dict, research_json: Dict) -> List[Dict]:
        """Run matcher agent - matches article structure with fallback logic"""
        # Build query from profile - matches article format
        program = student_profile.get('program', '')
        interests = student_profile.get('interests', [])
        career_goals = student_profile.get('career_goals', '')
        
        # Handle interests - could be list or string
        if isinstance(interests, str):
            # Handle comma-separated or space-separated
            if ',' in interests:
                interests_list = [i.strip() for i in interests.split(',') if i.strip()]
            else:
                # Split by spaces if no commas
                interests_list = [i.strip() for i in interests.split() if i.strip() and len(i.strip()) > 2]
        elif isinstance(interests, list):
            interests_list = [str(i).strip() for i in interests if i]
        else:
            interests_list = []
        
        # Build comprehensive query string
        query_parts = []
        if program:
            query_parts.append(program)
        if interests_list:
            query_parts.extend(interests_list[:5])  # Limit to top 5 interests
        if career_goals:
            # Extract key terms from career goals
            career_keywords = [word for word in career_goals.split() if len(word) > 4]
            query_parts.extend(career_keywords[:3])  # Add top 3 keywords
        
        query = ' '.join(query_parts) if query_parts else program or "university programs"
        
        # Build filters - matches article
        target_countries = student_profile.get("target_countries", [])
        budget = student_profile.get("budget")
        level = student_profile.get("level")
        
        # Try search with progressive filter relaxation
        search_attempts = [
            # Attempt 1: Full filters
            {
                "countries": target_countries if target_countries else None,
                "max_tuition": int(budget) if budget and budget > 0 else None,
                "level": str(level) if level else None
            },
            # Attempt 2: Without budget filter (budget might be too restrictive)
            {
                "countries": target_countries if target_countries else None,
                "level": str(level) if level else None
            },
            # Attempt 3: Only level filter
            {
                "level": str(level) if level else None
            },
            # Attempt 4: Only countries
            {
                "countries": target_countries if target_countries else None
            },
            # Attempt 5: No filters (semantic search only)
            {}
        ]
        
        # Try each search attempt until we get results
        for attempt_num, filters in enumerate(search_attempts, 1):
            # Clean up None values
            clean_filters = {k: v for k, v in filters.items() if v is not None and v != []}
            
            try:
                logging.info(f"Matcher attempt {attempt_num}: query='{query}', filters={clean_filters}")
                results = self.vector_db.search_universities(query, clean_filters if clean_filters else None, limit=20)
                if results and len(results) > 0:
                    logging.info(f"Matcher found {len(results)} results with attempt {attempt_num}")
                    return results
                else:
                    logging.info(f"Matcher attempt {attempt_num} returned 0 results")
            except Exception as e:
                logging.warning(f"Matcher search attempt {attempt_num} failed: {e}")
                continue
        
        # If all attempts failed, try a very basic search
        try:
            logging.info("Trying basic search without any filters")
            results = self.vector_db.search_universities(program or "university", None, limit=20)
            return results if results else []
        except Exception as e:
            logging.error(f"Matcher final search error: {e}")
            return []

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
Acceptance Rate: {uni.get('acceptance_rate', 0) * 100:.1f}%
Similarity Score: {uni.get('similarity_score', 0):.3f}
Research: {uni.get('research_output', 'N/A')}
Employment Rate: {uni.get('employment_rate_6mo', 0) * 100:.1f}%
""")
        return "\n".join(formatted)
