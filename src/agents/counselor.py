from crewai import Agent, Task
from typing import Dict, List
import json


class CounselorAgent:
    def __init__(self, llm):
        self.agent = Agent(
            role="University Admissions Counselor",
            goal="Provide personalized, actionable advice and create application timelines",
            backstory="""You are a seasoned university counselor with 15 years of experience 
            helping students navigate the complex application process. You provide clear, 
            empathetic guidance and create realistic timelines.""",
            llm=llm,
            verbose=True,
            allow_delegation=False
        )

    def create_advisory_task(self, student_profile: Dict, matched_universities: List) -> Task:
        """Create task to generate personalized advice"""
        return Task(
            description=f"""
            Create a comprehensive advisory report for this student including:

            1. **Personalized Recommendation Summary**
            - Why each recommended university is a good fit
            - Strengths and potential challenges
            - Unique opportunities at each institution

            2. **Application Timeline** (for the next 12 months)
            - Month-by-month action items
            - Key deadlines for each university
            - Language test preparation schedule
            - Document collection checklist

            3. **Financial Planning**
            - Total cost breakdown (tuition + living)
            - Scholarship opportunities
            - Part-time work possibilities

            4. **Preparation Checklist**
            - Documents needed
            - Test scores required
            - Recommendation letters
            - Statement of purpose tips

            5. **Next Steps** (immediate actions for next 2 weeks)

            Student Profile:
            {self._format_profile(student_profile)}

            Matched Universities:
            {matched_universities}

            Make the advice practical, encouraging, and specific.
            """,
            agent=self.agent,
            expected_output="Comprehensive advisory report with timeline and action items"
        )

    def _format_profile(self, profile: Dict) -> str:
        """Format student profile for readability"""
        lines = []
        for key, value in profile.items():
            if isinstance(value, list):
                lines.append(f"- {key.replace('_', ' ').title()}: {', '.join(map(str, value))}")
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")
        return "\n".join(lines)
