import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime


class UniversityRanker:
    """Advanced ranking system with multiple factors"""

    def __init__(self):
        self.weights = {
            'semantic_similarity': 0.30,
            'acceptance_fit': 0.20,
            'financial_fit': 0.20,
            'research_quality': 0.15,
            'employment_rate': 0.10,
            'deadline_urgency': 0.05
        }

    def calculate_acceptance_fit(self, acceptance_rate: float, student_strength: float) -> float:
        """
        Calculate how well student's profile matches acceptance rate
        student_strength: 0–1 scale (0.5 = average, 0.8 = strong, 0.9 = exceptional)
        """
        # Target: acceptance_rate should be ~2x student_strength for good fit
        ideal_acceptance = student_strength * 2
        difference = abs(acceptance_rate - ideal_acceptance)

        # Score decreases as difference increases
        score = max(0, 1 - (difference * 2))
        return score

    def calculate_financial_fit(self, tuition: int, budget: int, living_cost: int) -> float:
        """Calculate financial fit score"""
        total_cost = tuition + (living_cost * 12)  # Annual living cost

        if total_cost <= budget:
            return 1.0
        elif total_cost <= budget * 1.15:
            return 0.8
        elif total_cost <= budget * 1.30:
            return 0.5
        else:
            return 0.2

    def calculate_research_score(self, research_output: str) -> float:
        """Convert research output to score"""
        mapping = {
            'Very High': 1.0,
            'High': 0.8,
            'Good': 0.6,
            'Medium': 0.4
        }
        return mapping.get(research_output, 0.5)

    def calculate_deadline_score(self, deadline_str: str) -> float:
        """Score based on deadline urgency"""
        try:
            deadline = pd.to_datetime(deadline_str)
            today = pd.Timestamp.now()
            days_remaining = (deadline - today).days

            if days_remaining < 30:
                return 0.3  # Too urgent
            elif days_remaining < 90:
                return 0.7  # Tight but manageable
            elif days_remaining < 180:
                return 1.0  # Ideal timeframe
            else:
                return 0.9  # Plenty of time
        except Exception:
            return 0.5

    def rank_universities(self, universities: List[Dict], student_profile: Dict) -> List[Dict]:
        """Main ranking function"""
        student_strength = self._calculate_student_strength(student_profile)
        budget = student_profile.get('budget', 50000)

        for uni in universities:
            scores = {
                'semantic': uni['similarity_score'],
                'acceptance_fit': self.calculate_acceptance_fit(
                    uni['acceptance_rate'],
                    student_strength
                ),
                'financial_fit': self.calculate_financial_fit(
                    uni['tuition_usd'],
                    budget,
                    uni['living_cost_monthly']
                ),
                'research': self.calculate_research_score(uni['research_output']),
                'employment': uni['employment_rate_6mo'],
                'deadline': self.calculate_deadline_score(uni['deadline'])
            }

            # Weighted total score
            total_score = (
                scores['semantic'] * self.weights['semantic_similarity'] +
                scores['acceptance_fit'] * self.weights['acceptance_fit'] +
                scores['financial_fit'] * self.weights['financial_fit'] +
                scores['research'] * self.weights['research_quality'] +
                scores['employment'] * self.weights['employment_rate'] +
                scores['deadline'] * self.weights['deadline_urgency']
            )

            uni['final_score'] = round(total_score, 3)
            uni['score_breakdown'] = scores
            uni['category'] = self._categorize_university(
                scores['acceptance_fit'],
                student_strength
            )

        # Sort by final score
        universities.sort(key=lambda x: x['final_score'], reverse=True)
        return universities

    def _calculate_student_strength(self, profile: Dict) -> float:
        """Estimate student strength from profile (0–1 scale)"""
        gpa = profile.get('gpa', 3.0)
        work_exp = len(profile.get('work_experience', '').split()) > 5

        # Normalize GPA to 0–1 (assuming 4.0 scale)
        gpa_score = min(gpa / 4.0, 1.0)

        # Add bonus for work experience
        if work_exp:
            gpa_score = min(gpa_score + 0.1, 1.0)

        return gpa_score

    def _categorize_university(self, acceptance_fit: float, student_strength: float) -> str:
        """Categorize as reach/target/safety"""
        if acceptance_fit > 0.7:
            return "Target"
        elif student_strength > 0.7 and acceptance_fit > 0.4:
            return "Safety"
        else:
            return "Reach"

    def balance_portfolio(self, universities: List[Dict]) -> List[Dict]:
        """Ensure balanced portfolio: 30% reach, 40% target, 30% safety"""
        reach = [u for u in universities if u['category'] == 'Reach']
        target = [u for u in universities if u['category'] == 'Target']
        safety = [u for u in universities if u['category'] == 'Safety']

        portfolio = reach[:3] + target[:4] + safety[:3]
        return portfolio


# Test the ranker
if __name__ == "__main__":
    ranker = UniversityRanker()

    # Sample university
    test_unis = [
        {
            'univ_name': 'MIT',
            'similarity_score': 0.92,
            'acceptance_rate': 0.04,
            'tuition_usd': 55000,
            'living_cost_monthly': 2000,
            'research_output': 'Very High',
            'employment_rate_6mo': 0.95,
            'deadline': '2026-01-15'
        }
    ]

    test_profile = {
        'gpa': 3.8,
        'budget': 60000,
        'work_experience': 'Software engineer at Google for 2 years'
    }

    ranked = ranker.rank_universities(test_unis, test_profile)
    print("Final Score:", ranked[0]['final_score'])
    print("Category:", ranked[0]['category'])
    print("Breakdown:", ranked[0]['score_breakdown'])
