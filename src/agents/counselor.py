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

    def create_plan(self, matches: List[Dict], student_profile: Dict) -> str:
        """Create application plan - matches article structure"""
        name = student_profile.get('name', 'Student')
        target_countries = student_profile.get('target_countries', [])
        
        # Handle countries - could be list or string
        if isinstance(target_countries, str):
            countries_list = [c.strip() for c in target_countries.split(',') if c.strip()]
        elif isinstance(target_countries, list):
            countries_list = [str(c).strip() for c in target_countries if c]
        else:
            countries_list = []
        
        first_country = countries_list[0] if countries_list else 'target countries'
        num_matches = len(matches) if matches else 0
        
        num_countries = len(countries_list) if countries_list else 1
        country_word = 'countries' if num_countries > 1 else 'country'
        
        plan = f"""
### Application Plan for {name}

**Overview:**
- Target {num_matches} programs across {num_countries} {country_word}.

**Immediate Actions (Next 3 Months):**
- Schedule IELTS/GRE/TOEFL tests within 3 months
- Prepare Statement of Purpose (SOP) draft
- Request Recommendation Letters (LOR) from professors/employers
- Research scholarship opportunities for {first_country}

**Application Timeline:**
- Month 1-2: Complete language tests and gather documents
- Month 3-4: Finalize SOP and submit applications
- Month 5-6: Follow up on applications and prepare for interviews
- Month 7-8: Receive decisions and prepare visa documents

**Key Deadlines:**
- Check individual university deadlines (typically {first_country} deadlines are 6-12 months before program start)
- Scholarship applications often have earlier deadlines

**Next Steps:**
1. Review the recommended universities below
2. Visit official university websites to verify current deadlines
3. Start preparing required documents
4. Apply for scholarships in parallel with university applications
"""
        return plan

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
