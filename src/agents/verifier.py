"""
Verifier Agent - Validates critical information in recommendations
Checks deadlines, scholarship claims, and data accuracy
"""

from crewai import Agent, Task
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import re

from src.utils.groq_llm import create_groq_llm


class VerifierAgent:
    """
    Agent responsible for verifying critical information in recommendations.
    Ensures data accuracy, flags outdated information, and provides confidence scores.
    """
    
    def __init__(self, llm):
        self.agent = Agent(
            role="Information Verification Specialist",
            goal="Verify critical information like deadlines, scholarship availability, and admission requirements with high accuracy",
            backstory="""You are a meticulous fact-checker with 10 years of experience in 
            international education. You have an eye for detail and never let inaccurate 
            information slip through. You understand that students make life-changing 
            decisions based on this data, so accuracy is paramount. You flag uncertain 
            information and suggest verification methods.""",
            llm=llm,
            verbose=True,
            allow_delegation=False
        )
        
        # Confidence thresholds
        self.confidence_thresholds = {
            'high': 0.85,
            'medium': 0.60,
            'low': 0.40
        }
    
    def create_verification_task(self, recommendations: List[Dict], student_profile: Dict) -> Task:
        """
        Create task to verify critical information in recommendations
        
        Args:
            recommendations: List of university recommendations
            student_profile: Student's profile for context
            
        Returns:
            Task object for CrewAI to execute
        """
        verification_items = self._prepare_verification_items(recommendations)
        
        return Task(
            description=f"""
            Verify the following critical information from university recommendations:
            
            **Your Task:**
            For each university, verify:
            1. **Deadline Accuracy**
               - Is the deadline in the future?
               - Is there enough time to prepare? (minimum 30 days)
               - Are there multiple deadlines (early action, regular, etc.)?
            
            2. **Scholarship Claims**
               - Are scholarship names specific and verifiable?
               - Do eligibility criteria match student profile?
               - Are deadlines provided for scholarships?
            
            3. **Admission Requirements**
               - Are GPA/test score requirements clearly stated?
               - Are language requirements (IELTS/TOEFL) mentioned?
               - Are work experience requirements specified if needed?
            
            4. **Cost Estimates**
               - Does tuition seem accurate for the country/program?
               - Are living costs realistic?
               - Are there any red flags (too cheap, too expensive)?
            
            5. **Program Availability**
               - Does the program still accept international students?
               - Is the program currently active (not discontinued)?
            
            **Verification Items:**
            {verification_items}
            
            **Student Context:**
            - Origin: {student_profile.get('origin_country', 'Not specified')}
            - Budget: ${student_profile.get('budget', 'Not specified')}
            - Level: {student_profile.get('level', 'Not specified')}
            - Timeline: Applying in {datetime.now().strftime('%Y')}
            
            **Output Format:**
            For each university, provide:
            - Overall confidence score (0-100)
            - Specific flags for any issues found
            - Verification recommendations (where to double-check)
            - Risk level: LOW / MEDIUM / HIGH
            
            Be thorough but practical. Flag genuine concerns, not minor uncertainties.
            """,
            agent=self.agent,
            expected_output="""JSON object with verification results for each university:
            {
                "university_id": {
                    "confidence_score": 85,
                    "flags": ["deadline_tight", "scholarship_unverified"],
                    "verification_needed": ["Check official website for current deadlines"],
                    "risk_level": "MEDIUM",
                    "details": {...}
                }
            }"""
        )
    
    def _prepare_verification_items(self, recommendations: List[Dict]) -> str:
        """Format recommendations for verification prompt"""
        items = []
        
        for idx, rec in enumerate(recommendations, 1):
            item = f"""
            {idx}. {rec.get('univ_name', 'Unknown')} - {rec.get('program', 'Unknown')}
               - Deadline: {rec.get('deadline', 'Not specified')}
               - Tuition: ${rec.get('tuition_usd', 0):,}
               - Living Cost: ${rec.get('living_cost_monthly', 0):,}/month
               - Scholarships: {rec.get('scholarship_tags', 'none')}
               - Acceptance Rate: {rec.get('acceptance_rate', 0) * 100:.1f}%
               - Language: {rec.get('language', 'Not specified')}
            """
            items.append(item)
        
        return "\n".join(items)
    
    def verify_deadline(self, deadline_str: str) -> Dict:
        """
        Verify if a deadline is valid and provides adequate time
        
        Args:
            deadline_str: Deadline in string format (YYYY-MM-DD)
            
        Returns:
            Dictionary with verification results
        """
        try:
            deadline = pd.to_datetime(deadline_str)
            today = pd.Timestamp.now()
            days_remaining = (deadline - today).days
            
            # Check if deadline has passed
            if days_remaining < 0:
                return {
                    'valid': False,
                    'confidence': 0.0,
                    'flag': 'deadline_passed',
                    'message': f'Deadline has passed by {abs(days_remaining)} days',
                    'risk_level': 'HIGH'
                }
            
            # Check if deadline is too soon
            elif days_remaining < 30:
                return {
                    'valid': True,
                    'confidence': 0.5,
                    'flag': 'deadline_urgent',
                    'message': f'Only {days_remaining} days remaining - very tight timeline',
                    'risk_level': 'MEDIUM'
                }
            
            # Check if deadline is reasonable
            elif days_remaining < 90:
                return {
                    'valid': True,
                    'confidence': 0.8,
                    'flag': 'deadline_approaching',
                    'message': f'{days_remaining} days remaining - adequate time with focus',
                    'risk_level': 'LOW'
                }
            
            else:
                return {
                    'valid': True,
                    'confidence': 1.0,
                    'flag': None,
                    'message': f'{days_remaining} days remaining - comfortable timeline',
                    'risk_level': 'LOW'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'confidence': 0.0,
                'flag': 'deadline_invalid',
                'message': f'Could not parse deadline: {str(e)}',
                'risk_level': 'HIGH'
            }
    
    def verify_cost_accuracy(self, tuition: int, living_cost: int, 
                            country: str, level: str) -> Dict:
        """
        Verify if costs are realistic for the country/program
        
        Args:
            tuition: Annual tuition in USD
            living_cost: Monthly living cost in USD
            country: Country name
            level: Study level (bachelors/masters/phd)
            
        Returns:
            Dictionary with verification results
        """
        # Realistic cost ranges by country (annual tuition in USD)
        cost_ranges = {
            'USA': {
                'bachelors': (20000, 70000),
                'masters': (25000, 65000),
                'phd': (0, 40000)  # Often funded
            },
            'UK': {
                'bachelors': (15000, 40000),
                'masters': (15000, 45000),
                'phd': (15000, 35000)
            },
            'Canada': {
                'bachelors': (12000, 35000),
                'masters': (12000, 40000),
                'phd': (5000, 25000)
            },
            'Germany': {
                'bachelors': (0, 5000),
                'masters': (0, 5000),
                'phd': (0, 3000)
            },
            'Australia': {
                'bachelors': (20000, 45000),
                'masters': (22000, 50000),
                'phd': (18000, 42000)
            },
            'Netherlands': {
                'bachelors': (6000, 15000),
                'masters': (8000, 20000),
                'phd': (0, 5000)
            },
            'Sweden': {
                'bachelors': (0, 18000),
                'masters': (0, 20000),
                'phd': (0, 0)  # Usually free
            }
        }
        
        # Living cost ranges by country (monthly in USD)
        living_ranges = {
            'USA': (1200, 3000),
            'UK': (1000, 2500),
            'Canada': (900, 2000),
            'Germany': (800, 1500),
            'Australia': (1200, 2500),
            'Netherlands': (900, 1800),
            'Sweden': (900, 1600)
        }
        
        issues = []
        confidence = 1.0
        
        # Verify tuition
        if country in cost_ranges and level in cost_ranges[country]:
            min_tuition, max_tuition = cost_ranges[country][level]
            
            if tuition < min_tuition * 0.5:
                issues.append(f"Tuition (${tuition:,}) seems unusually low for {country}")
                confidence -= 0.3
            elif tuition > max_tuition * 1.5:
                issues.append(f"Tuition (${tuition:,}) seems unusually high for {country}")
                confidence -= 0.2
        
        # Verify living costs
        if country in living_ranges:
            min_living, max_living = living_ranges[country]
            
            if living_cost < min_living * 0.5:
                issues.append(f"Living cost (${living_cost}/mo) seems too low for {country}")
                confidence -= 0.2
            elif living_cost > max_living * 1.5:
                issues.append(f"Living cost (${living_cost}/mo) seems too high for {country}")
                confidence -= 0.2
        
        confidence = max(0.0, confidence)
        
        return {
            'valid': len(issues) == 0,
            'confidence': confidence,
            'flags': issues,
            'message': '; '.join(issues) if issues else 'Costs appear reasonable',
            'risk_level': 'HIGH' if confidence < 0.5 else 'MEDIUM' if confidence < 0.8 else 'LOW'
        }
    
    def verify_scholarship_eligibility(self, scholarship_tags: str, 
                                      student_profile: Dict) -> Dict:
        """
        Verify if student is eligible for mentioned scholarships
        
        Args:
            scholarship_tags: Comma-separated scholarship names
            student_profile: Student's profile
            
        Returns:
            Dictionary with eligibility verification
        """
        if not scholarship_tags or scholarship_tags == 'none':
            return {
                'valid': True,
                'confidence': 1.0,
                'flags': ['no_scholarships_mentioned'],
                'message': 'No scholarships mentioned',
                'risk_level': 'LOW'
            }
        
        scholarships = [s.strip() for s in scholarship_tags.split(',')]
        eligibility_checks = []
        
        origin_country = student_profile.get('origin_country', '').lower()
        gpa = student_profile.get('gpa', 0)
        
        for scholarship in scholarships:
            scholarship_lower = scholarship.lower()
            
            # Commonwealth scholarships
            if 'commonwealth' in scholarship_lower:
                commonwealth_countries = ['india', 'pakistan', 'bangladesh', 'nigeria', 
                                         'ghana', 'kenya', 'uganda', 'jamaica']
                if origin_country not in commonwealth_countries:
                    eligibility_checks.append(
                        f"Commonwealth scholarship typically for {', '.join(commonwealth_countries)}"
                    )
            
            # Merit-based scholarships
            if 'merit' in scholarship_lower:
                if gpa < 3.5:
                    eligibility_checks.append(
                        "Merit scholarships typically require GPA > 3.5"
                    )
            
            # Need-based scholarships
            if 'need' in scholarship_lower:
                if student_profile.get('budget', 0) > 40000:
                    eligibility_checks.append(
                        "Need-based scholarships typically for lower budgets"
                    )
        
        confidence = 1.0 - (len(eligibility_checks) * 0.2)
        confidence = max(0.3, confidence)
        
        return {
            'valid': len(eligibility_checks) == 0,
            'confidence': confidence,
            'flags': eligibility_checks,
            'message': '; '.join(eligibility_checks) if eligibility_checks 
                      else 'Appears eligible for mentioned scholarships',
            'risk_level': 'MEDIUM' if eligibility_checks else 'LOW'
        }
    
    def generate_verification_report(self, recommendations: List[Dict], 
                                    student_profile: Dict) -> Dict:
        """
        Generate comprehensive verification report for all recommendations
        
        Args:
            recommendations: List of university recommendations
            student_profile: Student's profile
            
        Returns:
            Complete verification report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_universities': len(recommendations),
            'verifications': {},
            'summary': {
                'high_confidence': 0,
                'medium_confidence': 0,
                'low_confidence': 0,
                'requires_attention': []
            }
        }
        
        for rec in recommendations:
            uni_id = rec.get('univ_id', rec.get('univ_name', 'unknown'))
            
            # Verify different aspects
            deadline_check = self.verify_deadline(rec.get('deadline', ''))
            cost_check = self.verify_cost_accuracy(
                rec.get('tuition_usd', 0),
                rec.get('living_cost_monthly', 0),
                rec.get('country', ''),
                rec.get('level', '')
            )
            scholarship_check = self.verify_scholarship_eligibility(
                rec.get('scholarship_tags', ''),
                student_profile
            )
            
            # Calculate overall confidence
            overall_confidence = (
                deadline_check['confidence'] * 0.4 +
                cost_check['confidence'] * 0.3 +
                scholarship_check['confidence'] * 0.3
            )
            
            # Collect all flags
            all_flags = []
            if deadline_check.get('flag'):
                all_flags.append(deadline_check['flag'])
            all_flags.extend(cost_check.get('flags', []))
            all_flags.extend(scholarship_check.get('flags', []))
            
            # Determine overall risk
            risk_levels = [
                deadline_check['risk_level'],
                cost_check['risk_level'],
                scholarship_check['risk_level']
            ]
            overall_risk = 'HIGH' if 'HIGH' in risk_levels else \
                          'MEDIUM' if 'MEDIUM' in risk_levels else 'LOW'
            
            verification = {
                'university': rec.get('univ_name'),
                'program': rec.get('program'),
                'overall_confidence': round(overall_confidence, 2),
                'risk_level': overall_risk,
                'checks': {
                    'deadline': deadline_check,
                    'costs': cost_check,
                    'scholarships': scholarship_check
                },
                'flags': all_flags,
                'recommendations': self._generate_recommendations(all_flags, rec)
            }
            
            report['verifications'][uni_id] = verification
            
            # Update summary
            if overall_confidence >= 0.85:
                report['summary']['high_confidence'] += 1
            elif overall_confidence >= 0.60:
                report['summary']['medium_confidence'] += 1
            else:
                report['summary']['low_confidence'] += 1
                report['summary']['requires_attention'].append({
                    'university': rec.get('univ_name'),
                    'reason': ', '.join(all_flags[:2])  # Top 2 issues
                })
        
        return report
    
    def _generate_recommendations(self, flags: List[str], university: Dict) -> List[str]:
        """Generate actionable recommendations based on flags"""
        recommendations = []
        
        if 'deadline_passed' in flags:
            recommendations.append(" This university's deadline has passed. Remove from list.")
        
        if 'deadline_urgent' in flags:
            recommendations.append(" Deadline is very soon. Prioritize this application or consider skipping.")
        
        if 'deadline_approaching' in flags:
            recommendations.append(" Start application process immediately.")
        
        if any('cost' in f.lower() for f in flags):
            recommendations.append(" Verify costs on official university website.")
        
        if any('scholarship' in f.lower() for f in flags):
            recommendations.append(" Check scholarship eligibility criteria carefully.")
        
        if not recommendations:
            recommendations.append(" All checks passed. Proceed with application.")
        
        return recommendations


# Utility function for standalone verification
def quick_verify(university: Dict, student_profile: Dict) -> Dict:
    """
    Quick verification function for single university
    
    Args:
        university: University data dictionary
        student_profile: Student profile dictionary
        
    Returns:
        Verification results
    """
    # Create a dummy LLM config (won't be used for quick checks)
    dummy_llm = create_groq_llm(model='llama-3.1-8b-instant', temperature=0.7)
    verifier = VerifierAgent(llm=dummy_llm)
    
    return verifier.generate_verification_report([university], student_profile)


if __name__ == "__main__":
    # Test the verifier
    test_university = {
        'univ_id': 'test-001',
        'univ_name': 'Test University',
        'program': 'Computer Science',
        'country': 'USA',
        'level': 'masters',
        'tuition_usd': 45000,
        'living_cost_monthly': 1800,
        'deadline': '2026-03-15',
        'scholarship_tags': 'merit_based,department_fellowship'
    }
    
    test_profile = {
        'origin_country': 'India',
        'gpa': 3.7,
        'budget': 50000
    }
    
    dummy_llm = create_groq_llm(model='llama-3.1-8b-instant', temperature=0.7)
    verifier = VerifierAgent(llm=dummy_llm)
    report = verifier.generate_verification_report([test_university], test_profile)
    
    print("Verification Report:")
    print(f"Overall Confidence: {report['verifications']['test-001']['overall_confidence']}")
    print(f"Risk Level: {report['verifications']['test-001']['risk_level']}")
    print(f"Flags: {report['verifications']['test-001']['flags']}")
    print(f"Recommendations: {report['verifications']['test-001']['recommendations']}")