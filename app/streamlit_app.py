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
        col1.metric("Country", uni['country'])
        col2.metric("Tuition", f"${uni['tuition_usd']:,}")
        col3.metric("Match Score", f"{uni.get('final_score', 0):.2%}")
        col4.metric("Category", uni.get('category', 'Target'))

        with st.expander("Detailed Breakdown"):
            col_a, col_b = st.columns(2)

            with col_a:
                st.write("**Academic Info:**")
                st.write(f"- Acceptance Rate: {uni['acceptance_rate'] * 100:.1f}%")
                st.write(f"- Research Output: {uni['research_output']}")
                st.write(f"- Average Class Size: {uni['avg_class_size']}")
                st.write(f"- Language: {uni['language']}")

            with col_b:
                st.write("**Practical Info:**")
                st.write(f"- Application Deadline: {uni['deadline']}")
                st.write(f"- Living Cost: ${uni['living_cost_monthly']}/month")
                st.write(f"- Visa Difficulty: {uni['visa_difficulty']}")
                st.write(f"- Employment Rate: {uni['employment_rate_6mo'] * 100:.1f}%")

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
    df = pd.DataFrame(universities)

    col1, col2 = st.columns(2)

    with col1:
        category_counts = df['category'].value_counts()
        fig_pie = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="University Categories",
            color_discrete_map={'Reach': '#FF6B6B', 'Target': '#4ECDC4', 'Safety': '#95E1D3'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        fig_scatter = px.scatter(
            df,
            x='tuition_usd',
            y='final_score',
            size='acceptance_rate',
            color='country',
            hover_data=['univ_name', 'program'],
            title="Tuition vs Match Score",
            labels={'tuition_usd': 'Annual Tuition (USD)', 'final_score': 'Match Score'}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    fig_bar = px.bar(
        x=df['country'].value_counts().index,
        y=df['country'].value_counts().values,
        title="Universities by Country",
        labels={'x': 'Country', 'y': 'Count'},
        color=df['country'].value_counts().values,
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
        db = load_database()
        collection_info = db.client.get_collection(db.collection_name)
        st.metric("Universities Indexed", collection_info.points_count)
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
                        ranker = UniversityRanker()

                        query_parts = []
                        if profile['interests']:
                            query_parts.append(f"Interests: {', '.join(profile['interests'])}")
                        query_parts.append(f"Program: {profile['program']}")
                        if profile['career_goals']:
                            query_parts.append(f"Goals: {profile['career_goals']}")

                        search_query = " | ".join(query_parts)

                        results = db.search_universities(
                            query=search_query,
                            filters={
                                'countries': profile['target_countries'],
                                'max_tuition': profile['budget'],
                                'level': profile['level']
                            },
                            limit=20
                        )

                        ranked = ranker.rank_universities(results, profile)
                        portfolio = ranker.balance_portfolio(ranked)

                        st.session_state.recommendations = portfolio
                        st.session_state.search_history.append(profile)

                        st.success(f"Found {len(portfolio)} great matches for you!")
                        st.balloons()

                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                        st.info("Make sure Qdrant is running and data is loaded!")

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
