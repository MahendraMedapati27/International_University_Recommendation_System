import pandas as pd
import random
from datetime import datetime, timedelta
from tqdm import tqdm

def generate_sample_data():
    """Generate realistic university dataset"""
    countries = ['UK', 'USA', 'Canada', 'Germany', 'Australia', 'Netherlands', 'Sweden']
    programs = ['Computer Science', 'Data Science', 'Renewable Energy', 'Business Analytics',
                'Mechanical Engineering', 'Biomedical Engineering', 'Economics', 'Psychology']
    levels = ['bachelors', 'masters', 'phd']
    languages = ['English', 'German', 'Swedish', 'Dutch']

    universities = []

    uni_names = {
        'UK': ['Oxford University', 'Cambridge University', 'Imperial College London', 'UCL', 'Edinburgh University'],
        'USA': ['MIT', 'Stanford University', 'Harvard University', 'UC Berkeley', 'Carnegie Mellon'],
        'Canada': ['University of Toronto', 'UBC', 'McGill University', 'Waterloo University'],
        'Germany': ['TU Munich', 'RWTH Aachen', 'University of Heidelberg', 'Humboldt University'],
        'Australia': ['ANU', 'University of Melbourne', 'UNSW', 'Monash University'],
        'Netherlands': ['TU Delft', 'University of Amsterdam', 'Eindhoven University', 'Leiden University'],
        'Sweden': ['KTH Royal Institute', 'Lund University', 'Uppsala University']
    }

    tuition_ranges = {
        'UK': (18000, 35000),
        'USA': (30000, 60000),
        'Canada': (15000, 35000),
        'Germany': (0, 3000),
        'Australia': (25000, 45000),
        'Netherlands': (8000, 20000),
        'Sweden': (0, 15000)
    }

    id_counter = 1
    for country in tqdm(countries, desc="Generating universities"):
        for uni_name in uni_names[country]:
            for program in programs[:4]:  # 4 programs per university
                for level in levels[:2]:  # bachelors and masters

                    tuition = random.randint(*tuition_ranges[country])

                    # Determine language
                    lang = 'English'
                    if country == 'Germany':
                        lang = random.choice(['English', 'German'])
                    elif country == 'Sweden':
                        lang = random.choice(['English', 'Swedish'])
                    elif country == 'Netherlands':
                        lang = random.choice(['English', 'Dutch'])

                    # Generate deadline
                    deadline = datetime.now() + timedelta(days=random.randint(30, 365))

                    # Acceptance rate proxy
                    acceptance = round(random.uniform(0.05, 0.45), 2)

                    # Scholarship tags
                    scholarships = []
                    if random.random() > 0.5:
                        scholarships.append('merit_based')
                    if random.random() > 0.6:
                        scholarships.append('need_based')
                    if country in ['UK', 'Canada', 'Australia']:
                        if random.random() > 0.7:
                            scholarships.append('commonwealth')

                    # Always ensure at least one scholarship tag
                    if 'merit_based' not in scholarships:
                        scholarships.append('merit_based')

                    # Generate detailed description
                    description = f"""
                    The {program} program at {uni_name} offers a cutting-edge curriculum focusing on
                    theoretical foundations and practical applications. Students benefit from world-class
                    faculty, state-of-the-art research facilities, and strong industry connections.
                    The program emphasizes {'research methodology' if level == 'masters' else 'foundational skills'}
                    and prepares graduates for {'advanced research or industry leadership' if level == 'masters' else 'successful careers'}.

                    Entry requirements: {'Bachelor degree with 2:1 or equivalent, relevant experience preferred' if level == 'masters'
                    else 'High school diploma with strong grades in relevant subjects'}.

                    Career prospects: Graduates typically find positions in {'senior roles at tech companies, research institutions, or pursue PhD studies'
                    if level == 'masters' else 'entry to mid-level positions across various industries'}.
                    """

                    universities.append({
                        'univ_id': f'{country.lower()[:3]}-{id_counter:03d}',
                        'univ_name': uni_name,
                        'country': country,
                        'program': program,
                        'level': level,
                        'tuition_usd': tuition,
                        'deadline': deadline.strftime('%Y-%m-%d'),
                        'language': lang,
                        'acceptance_rate': acceptance,
                        'scholarship_tags': ','.join(scholarships) if scholarships else 'none',
                        'description': description.strip(),
                        'qs_ranking': random.randint(20, 500) if random.random() > 0.3 else None,
                        'research_output': random.choice(['Very High', 'High', 'Medium', 'Good']),
                        'living_cost_monthly': random.randint(800, 2500),
                        'visa_difficulty': random.choice(['Easy', 'Moderate', 'Challenging']),
                        'avg_class_size': random.randint(15, 80),
                        'employment_rate_6mo': round(random.uniform(0.70, 0.95), 2)
                    })
                    id_counter += 1

    df = pd.DataFrame(universities)
    df.to_csv('data/raw/universities_sample.csv', index=False)
    print(f"Generated {len(universities)} university programs")
    return df

if __name__ == "__main__":
    df = generate_sample_data()
    print(df.head())
