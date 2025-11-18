import streamlit as st
import sys
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.qdrant_client import UniversityVectorDB
from src.crew.coordinator import UniversityRecommendationCrew
from src.utils.ranking import UniversityRanker


# --------------------------- #
# Page Configuration
# --------------------------- #
st.set_page_config(
page_title="University Recommender",
    page_icon="🎓",
layout="wide",
initial_sidebar_state="expanded"
)

# --------------------------- #
# Custom CSS
# --------------------------- #
st.markdown("""
<style>
.big-font {
font-size:30px!important;
font-weight: bold;
}
.metric-card {
background-color: #f0f2f6;
padding: 20px;
border-radius: 10px;
margin: 10px 0;
    color: #1f2937;
}
.metric-card h3 {
    color: #1f2937 !important;
    font-weight: bold;
}
.metric-card p {
    color: #374151 !important;
}
.stButton>button {
width: 100%;
background-color: #4CAF50;
color: white;
height: 3em;
border-radius: 8px;
}
/* Dark theme compatibility */
[data-testid="stAppViewContainer"] {
    background-color: #0e1117;
}
/* Ensure text contrast in recommendation cards */
.metric-card h3, .metric-card p {
    color: #1f2937 !important;
}
/* Fix any light text on light backgrounds */
div[data-testid="metric-container"] {
    background-color: transparent;
}
</style>
""", unsafe_allow_html=True)


# --------------------------- #
# Session State
# --------------------------- #
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'search_history' not in st.session_state:
    st.session_state.search_history = []


# --------------------------- #
# Cached Loaders
# --------------------------- #
@st.cache_resource
def load_database():
    """Load and cache the vector database"""
    return UniversityVectorDB()


@st.cache_resource
def load_crew(_db):
    """Load and cache the CrewAI coordinator"""
    return UniversityRecommendationCrew(_db)


# --------------------------- #
# Form - Student Profile
# --------------------------- #
def create_profile_form():
    """Create the student profile input form"""
    st.markdown("<p class='big-font'>Tell Us About Yourself</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Full Name", placeholder="e.g., Priya Sharma")
        origin_country = st.selectbox(
            "Where are you from?",
            ["India", "China", "USA", "UK", "Canada", "Nigeria", "Pakistan",
             "Bangladesh", "Vietnam", "Other"]
        )

        program = st.selectbox(
            "Program of Interest",
            ["Computer Science", "Data Science", "Business Analytics",
             "Mechanical Engineering", "Electrical Engineering",
             "Economics", "Psychology", "Renewable Energy",
             "Biomedical Engineering", "Other"]
        )

        level = st.selectbox("Study Level", ["bachelors", "masters", "phd"])

        gpa = st.slider(
            "GPA / Academic Score (4.0 scale)",
            min_value=2.0,
            max_value=4.0,
            value=3.5,
            step=0.1
        )

    with col2:
        target_countries = st.multiselect(
            "Preferred Countries",
            ["USA", "UK", "Canada", "Germany", "Australia",
             "Netherlands", "Sweden", "France", "Switzerland"],
            default=["USA", "UK"]
        )

        budget = st.number_input(
            "Annual Budget (USD)",
            min_value=0,
            max_value=100000,
            value=30000,
            step=5000,
            help="Include tuition + living costs"
        )

        interests = st.text_area(
            "Research Interests / Focus Areas",
            placeholder="e.g., Artificial Intelligence, Machine Learning, Computer Vision",
            height=100
        )

        career_goals = st.text_input(
            "Career Goals",
            placeholder="e.g., Data Scientist at FAANG, Research in academia"
        )

        work_experience = st.text_area(
            "Work Experience (if any)",
            placeholder="e.g., Software Engineer at Google for 2 years",
            height=80
        )

    profile = {
        'name': name,
        'origin_country': origin_country,
        'target_countries': target_countries,
        'program': program,
        'level': level,
        'budget': budget,
        'gpa': gpa,
        'interests': [i.strip() for i in interests.split(',') if i.strip()],
        'career_goals': career_goals,
        'work_experience': work_experience,
        'timestamp': datetime.now().isoformat()
    }

    return profile


# --------------------------- #
# University Card Component
# --------------------------- #
def display_university_card(uni: dict, rank: int):
    """Display a single university recommendation card"""
    emoji_map = {'Reach': '🚀', 'Target': '🎯', 'Safety': '🛡️'}

    with st.container():
        st.markdown(f"""
        <div class='metric-card'>
                    <h3>{rank}. {emoji_map.get(uni.get('category', 'Target'), '')} {uni['univ_name']}</h3>
        <p><strong>{uni['program']}</strong> ({uni['level'].title()})</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Country", uni.get('country', 'Unknown'))
        
        # Safely format tuition
        tuition = uni.get('tuition_usd', 0)
        if isinstance(tuition, str):
            try:
                tuition = float(tuition) if tuition and tuition != 'N/A' else 0
            except (ValueError, TypeError):
                tuition = 0
        elif not isinstance(tuition, (int, float)):
            tuition = 0
        tuition_str = f"${int(tuition):,}" if tuition > 0 else "N/A"
        col2.metric("Tuition", tuition_str)
        
        # Safely format match score
        final_score = uni.get('final_score', 0)
        if isinstance(final_score, str):
            try:
                final_score = float(final_score)
            except (ValueError, TypeError):
                final_score = 0
        elif not isinstance(final_score, (int, float)):
            final_score = 0
        score_str = f"{final_score:.2%}" if final_score > 0 else "N/A"
        col3.metric("Match Score", score_str)
        
        col4.metric("Category", uni.get('category', 'Target'))

        with st.expander("Detailed Breakdown"):
            col_a, col_b = st.columns(2)

            with col_a:
                st.write("**Academic Info:**")
                # Safely format acceptance rate
                acceptance_rate = uni.get('acceptance_rate', 0)
                if isinstance(acceptance_rate, str):
                    try:
                        acceptance_rate = float(acceptance_rate)
                    except (ValueError, TypeError):
                        acceptance_rate = 0
                elif not isinstance(acceptance_rate, (int, float)):
                    acceptance_rate = 0
                st.write(f"- Acceptance Rate: {acceptance_rate * 100:.1f}%")
                st.write(f"- Research Output: {uni.get('research_output', 'N/A')}")
                
                # Safely format class size
                class_size = uni.get('avg_class_size', 0)
                if isinstance(class_size, str):
                    try:
                        class_size = int(class_size)
                    except (ValueError, TypeError):
                        class_size = 0
                elif not isinstance(class_size, (int, float)):
                    class_size = 0
                st.write(f"- Average Class Size: {class_size if class_size > 0 else 'N/A'}")
                st.write(f"- Language: {uni.get('language', 'N/A')}")

            with col_b:
                st.write("**Practical Info:**")
                st.write(f"- Application Deadline: {uni.get('deadline', 'N/A')}")
                
                # Safely format living cost
                living_cost = uni.get('living_cost_monthly', 0)
                if isinstance(living_cost, str):
                    try:
                        living_cost = float(living_cost) if living_cost and living_cost != 'N/A' else 0
                    except (ValueError, TypeError):
                        living_cost = 0
                elif not isinstance(living_cost, (int, float)):
                    living_cost = 0
                living_cost_str = f"${int(living_cost):,}" if living_cost > 0 else "N/A"
                st.write(f"- Living Cost: {living_cost_str}/month")
                st.write(f"- Visa Difficulty: {uni.get('visa_difficulty', 'N/A')}")
                
                # Safely format employment rate
                employment_rate = uni.get('employment_rate_6mo', 0)
                if isinstance(employment_rate, str):
                    try:
                        employment_rate = float(employment_rate)
                    except (ValueError, TypeError):
                        employment_rate = 0
                elif not isinstance(employment_rate, (int, float)):
                    employment_rate = 0
                st.write(f"- Employment Rate: {employment_rate * 100:.1f}%")

            if uni.get('scholarship_tags') and uni['scholarship_tags'] != 'none':
                st.write(f"**Scholarships:** {uni['scholarship_tags']}")

            st.write("**Program Description:**")
            st.write(uni['description'][:300] + "...")

            # Score radar chart
            if 'score_breakdown' in uni:
                fig = go.Figure(data=go.Scatterpolar(
                    r=list(uni['score_breakdown'].values()),
                    theta=list(uni['score_breakdown'].keys()),
                    fill='toself'
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                    showlegend=False,
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)


# --------------------------- #
# Visualization Section
# --------------------------- #
def visualize_recommendations(universities: list):
    """Visualize recommendation results"""
    st.subheader("🎓 Portfolio Overview")

    if not universities or len(universities) == 0:
        st.warning("No recommendations to visualize.")
        return

    df = pd.DataFrame(universities)

    col1, col2 = st.columns(2)

    with col1:
        # Handle missing category field
        if 'category' in df.columns:
            category_counts = df['category'].value_counts()
            fig_pie = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                title="University Categories",
                color_discrete_map={'Reach': '#FF6B6B', 'Target': '#4ECDC4', 'Safety': '#95E1D3'}
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            # If no category, show country distribution instead
            if 'country' in df.columns:
                country_counts = df['country'].value_counts()
                fig_pie = px.pie(
                    values=country_counts.values,
                    names=country_counts.index,
                    title="Universities by Country"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No category data available for visualization.")

    with col2:
        # Ensure required columns exist and are numeric
        if 'tuition_usd' in df.columns and 'final_score' in df.columns:
            # Convert to numeric, handling strings
            df['tuition_usd'] = pd.to_numeric(df['tuition_usd'], errors='coerce').fillna(0)
            df['final_score'] = pd.to_numeric(df['final_score'], errors='coerce').fillna(0)
            
            # Handle acceptance_rate
            if 'acceptance_rate' in df.columns:
                df['acceptance_rate'] = pd.to_numeric(df['acceptance_rate'], errors='coerce').fillna(0.5)
            else:
                df['acceptance_rate'] = 0.5
            
            # Handle country
            if 'country' not in df.columns:
                df['country'] = 'Unknown'
            
            fig_scatter = px.scatter(
                df,
                x='tuition_usd',
                y='final_score',
                size='acceptance_rate',
                color='country',
                hover_data=['univ_name', 'program'] if 'univ_name' in df.columns and 'program' in df.columns else [],
                title="Tuition vs Match Score",
                labels={'tuition_usd': 'Annual Tuition (USD)', 'final_score': 'Match Score'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Insufficient data for scatter plot. Showing country distribution instead.")
            if 'country' in df.columns:
                country_counts = df['country'].value_counts()
                fig_bar = px.bar(
                    x=country_counts.index,
                    y=country_counts.values,
                    title="Universities by Country",
                    labels={'x': 'Country', 'y': 'Count'}
                )
                st.plotly_chart(fig_bar, use_container_width=True)

    # Country distribution bar chart
    if 'country' in df.columns:
        country_counts = df['country'].value_counts()
        fig_bar = px.bar(
            x=country_counts.index,
            y=country_counts.values,
            title="Universities by Country",
            labels={'x': 'Country', 'y': 'Count'},
            color=country_counts.values,
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_bar, use_container_width=True)


# --------------------------- #
# Main Function
# --------------------------- #
def main():
    st.markdown("<h1 style='text-align:center;'>🎓 AI University Recommender</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size:18px;'>Find your perfect university match powered by AI</p>", unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100.png?text=UniMatch+AI", use_container_width=True)
        st.markdown("---")
        st.markdown("### About")
        st.info("""
        This intelligent system uses:
        - **Semantic Search** (Qdrant)
        - **Multi-Agent AI** (CrewAI)
        - **Smart Ranking** algorithms
        """)
        try:
            db = load_database()
            # Check if collection exists and get info
            try:
                collection_info = db.client.get_collection(db.collection_name)
                st.metric("Universities Indexed", collection_info.points_count)
            except Exception as e:
                st.warning(f"⚠️ Could not connect to Qdrant: {str(e)}")
                st.info("💡 Make sure Qdrant is running: `docker run -p 6333:6333 qdrant/qdrant`")
                st.metric("Universities Indexed", "N/A")
        except Exception as e:
            st.error(f"Database connection error: {str(e)}")
            st.metric("Universities Indexed", "Error")

        if st.session_state.search_history:
            st.metric("Your Searches", len(st.session_state.search_history))

    tab1, tab2, tab3 = st.tabs(["🔍 Find Universities", "💡 My Recommendations", "⚙️ How It Works"])

    # --- Tab 1 ---
    with tab1:
        profile = create_profile_form()

        if st.button("Find My Universities", type="primary"):
            if not profile['name'] or not profile['target_countries']:
                st.error("Please fill in at least your name and target countries!")
            else:
                with st.spinner("AI agents are analyzing your profile..."):
                    try:
                        db = load_database()
                        
                        # Verify collection exists and is properly configured
                        if not db.verify_collection():
                            st.warning("⚠️ Collection not found or misconfigured. Please reinitialize the database.")
                            if st.button("🔄 Reinitialize Database"):
                                with st.spinner("Reinitializing database..."):
                                    try:
                                        db.create_collection()
                                        db.load_universities('data/raw/universities_sample.csv')
                                        st.success("✅ Database reinitialized successfully!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Failed to reinitialize: {e}")
                            return
                        
                        # Use the new pipeline approach - matches article structure
                        from src.crew.coordinator import UniversityRecommendationCrew
                        crew = load_crew(db)
                        
                        # Run the recommendation pipeline
                        result = crew.run_recommendation_process(profile)
                        
                        # Extract matches from pipeline result
                        matches = result.get('recommendations', {}).get('matches', [])
                        
                        # If no matches from pipeline, try a direct search as fallback
                        if not matches or len(matches) == 0:
                            st.info("🔄 Pipeline returned no matches. Trying direct search with relaxed filters...")
                            try:
                                # Build query
                                program = profile.get('program', '')
                                interests = profile.get('interests', [])
                                if isinstance(interests, list):
                                    interests_str = ' '.join(interests[:3])
                                else:
                                    interests_str = str(interests)
                                query = f"{program} {interests_str}".strip()
                                
                                # Try search with only level filter (most important)
                                level = profile.get('level', '')
                                filters = {'level': level} if level else None
                                
                                matches = db.search_universities(query, filters, limit=20)
                                
                                if not matches:
                                    # Try without any filters
                                    matches = db.search_universities(query, None, limit=20)
                                
                                if matches:
                                    st.success(f"✅ Found {len(matches)} matches with relaxed filters!")
                            except Exception as e:
                                st.warning(f"Fallback search also failed: {e}")
                        
                        # Debug: Show what was searched
                        if not matches:
                            with st.expander("🔍 Debug Information", expanded=True):
                                st.write("**Profile submitted:**")
                                st.json(profile)
                                st.write("**Search query would be:**")
                                program = profile.get('program', '')
                                interests = profile.get('interests', [])
                                if isinstance(interests, list):
                                    interests_str = ', '.join(interests)
                                else:
                                    interests_str = str(interests)
                                query = f"{program} {interests_str}"
                                st.code(query)
                                st.write("**Filters applied:**")
                                filters_info = {
                                    "countries": profile.get('target_countries', []),
                                    "max_tuition": profile.get('budget'),
                                    "level": profile.get('level')
                                }
                                st.json(filters_info)
                                
                                # Try a direct search to see if Qdrant is working
                                st.write("**Testing direct Qdrant search...**")
                                try:
                                    test_query = program or "Computer Science"
                                    test_results = db.search_universities(test_query, None, limit=5)
                                    if test_results:
                                        st.success(f"✅ Qdrant is working! Found {len(test_results)} results for '{test_query}'")
                                        st.write("Sample results:")
                                        for i, r in enumerate(test_results[:3], 1):
                                            tuition = r.get('tuition_usd', 0)
                                            level = r.get('level', 'N/A')
                                            country = r.get('country', 'Unknown')
                                            univ_name = r.get('univ_name', 'Unknown')
                                            program = r.get('program', 'Unknown')
                                            
                                            # Format tuition safely
                                            if isinstance(tuition, (int, float)) and tuition > 0:
                                                tuition_str = f"${int(tuition):,}"
                                            else:
                                                tuition_str = "N/A"
                                            
                                            st.write(f"{i}. {univ_name} - {program} ({country}) | Level: {level} | Tuition: {tuition_str}")
                                        
                                        # Check why filters might be failing
                                        st.write("**Filter Analysis:**")
                                        test_level = profile.get('level', '')
                                        test_countries = profile.get('target_countries', [])
                                        test_budget = profile.get('budget', 0)
                                        
                                        # Check sample results against filters
                                        matching_level = [r for r in test_results if r.get('level', '').lower() == test_level.lower()]
                                        matching_countries = [r for r in test_results if r.get('country') in test_countries]
                                        
                                        # Safely check budget - handle string/numeric types
                                        matching_budget = []
                                        for r in test_results:
                                            tuition = r.get('tuition_usd', 0)
                                            # Convert to numeric if possible
                                            if isinstance(tuition, str):
                                                try:
                                                    tuition = float(tuition) if tuition and tuition != 'N/A' else 0
                                                except (ValueError, TypeError):
                                                    tuition = 0
                                            elif not isinstance(tuition, (int, float)):
                                                tuition = 0
                                            
                                            if isinstance(tuition, (int, float)) and tuition > 0 and tuition <= test_budget * 1.2:
                                                matching_budget.append(r)
                                        
                                        st.write(f"- Results matching level '{test_level}': {len(matching_level)}/{len(test_results)}")
                                        st.write(f"- Results matching countries {test_countries}: {len(matching_countries)}/{len(test_results)}")
                                        st.write(f"- Results within budget ${test_budget:,} (+20% buffer): {len(matching_budget)}/{len(test_results)}")
                                        
                                        if len(matching_budget) == 0 and test_budget > 0:
                                            tuition_values = [r.get('tuition_usd', 0) for r in test_results if isinstance(r.get('tuition_usd'), (int, float)) and r.get('tuition_usd', 0) > 0]
                                            if tuition_values:
                                                min_tuition = min(tuition_values)
                                                st.warning(f"💡 Your budget of ${int(test_budget):,} might be too low. Sample results show minimum tuition of ${int(min_tuition):,}. Try increasing your budget or removing the budget filter.")
                                            else:
                                                st.warning(f"💡 Your budget of ${int(test_budget):,} might be too restrictive. Try increasing your budget or removing the budget filter.")
                                    else:
                                        st.warning("⚠️ Qdrant search returned no results even without filters")
                                except Exception as e:
                                    st.error(f"❌ Qdrant search error: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                        
                        portfolio = None
                        if matches and len(matches) > 0:
                            # Use ranker for additional ranking if available
                            try:
                                ranker = UniversityRanker()
                                ranked = ranker.rank_universities(matches, profile)
                                portfolio = ranker.balance_portfolio(ranked)
                            except Exception as e:
                                # Fallback to direct matches if ranker fails
                                st.warning(f"Ranker failed, using direct matches: {e}")
                                portfolio = matches[:10] if len(matches) > 10 else matches
                                
                                # Add default category and score for visualization
                                for uni in portfolio:
                                    if 'category' not in uni:
                                        # Simple categorization based on acceptance rate
                                        acceptance = uni.get('acceptance_rate', 0.5)
                                        if isinstance(acceptance, str):
                                            try:
                                                acceptance = float(acceptance)
                                            except:
                                                acceptance = 0.5
                                        
                                        if acceptance > 0.4:
                                            uni['category'] = 'Safety'
                                        elif acceptance > 0.2:
                                            uni['category'] = 'Target'
                                        else:
                                            uni['category'] = 'Reach'
                                    
                                    if 'final_score' not in uni:
                                        # Use similarity score as fallback
                                        score = uni.get('similarity_score', 0.5)
                                        if isinstance(score, str):
                                            try:
                                                score = float(score)
                                            except:
                                                score = 0.5
                                        uni['final_score'] = score
                            
                            # Ensure portfolio is not empty
                            if portfolio and len(portfolio) > 0:
                                st.session_state.recommendations = portfolio
                                if profile not in st.session_state.search_history:
                                    st.session_state.search_history.append(profile)

                                st.success(f"✅ Found {len(portfolio)} great matches for you!")
                                st.balloons()
                                
                                # Show application plan - update with actual match count
                                plan = result.get('recommendations', {}).get('plan', '')
                                if plan:
                                    # Update the plan with actual number of matches
                                    import re
                                    # Replace "Target 0 programs" or any number with actual count
                                    updated_plan = re.sub(
                                        r'Target \d+ programs',
                                        f'Target {len(portfolio)} programs',
                                        plan
                                    )
                                    
                                    with st.expander("📋 Application Plan", expanded=False):
                                        st.markdown(updated_plan)
                                else:
                                    # Generate a new plan if one doesn't exist
                                    from src.agents.counselor import CounselorAgent
                                    from src.utils.groq_llm import create_groq_llm
                                    counselor = CounselorAgent(create_groq_llm())
                                    new_plan = counselor.create_plan(portfolio, profile)
                                    with st.expander("📋 Application Plan", expanded=False):
                                        st.markdown(new_plan)
                                
                                # Show verification issues if any
                                issues = result.get('recommendations', {}).get('issues', [])
                                if issues:
                                    st.warning(f"⚠️ Found {len(issues)} potential issues with deadlines")
                                    with st.expander("View Issues", expanded=False):
                                        for issue in issues:
                                            st.write(f"- {issue.get('university', 'Unknown')}: {issue.get('issue', 'N/A')}")
                            else:
                                st.warning("No valid recommendations to display.")
                        else:
                            st.warning("No matches found. Try adjusting your criteria.")

                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                        import traceback
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())
                        st.info("💡 Make sure Qdrant is running: `docker run -p 6333:6333 qdrant/qdrant`")

    # --- Tab 2 ---
    with tab2:
        if st.session_state.recommendations:
            st.markdown("## 🎯 Your Personalized University Portfolio")
            visualize_recommendations(st.session_state.recommendations)
            st.markdown("---")
            st.markdown("## 🏫 Detailed Recommendations")

            for idx, uni in enumerate(st.session_state.recommendations, 1):
                display_university_card(uni, idx)

            df_download = pd.DataFrame(st.session_state.recommendations)
            csv = df_download.to_csv(index=False)
            st.download_button(
                label="📥 Download Recommendations (CSV)",
                data=csv,
                file_name=f"university_recommendations_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No recommendations yet. Fill out the form in the 'Find Universities' tab!")

    # --- Tab 3 ---
    with tab3:
        st.markdown("## ⚙️ How This System Works")
        st.markdown("""
        #### The Magic Behind the Scenes
        - **Semantic Understanding (Qdrant)**: Understands *meaning*, not just keywords.
        - **Multi-Agent Intelligence (CrewAI)**: Four agents collaborate for best matches.
        - **Smart Ranking**: Balances academic, financial, and research factors.
        - **Balanced Portfolio**: 30% Reach, 40% Target, 30% Safety.
        """)
        st.image("https://via.placeholder.com/800x400.png?text=System+Architecture+Diagram", use_container_width=True)


# --------------------------- #
# Run the App
# --------------------------- #
if __name__ == "__main__":
    main()
