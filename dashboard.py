"""
Streamlit Dashboard for Premier League Media Sentiment Tracker
"""

import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="⚽ Premier League Sentiment",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3.5rem;
        font-weight: bold;
        text-align: center;
        color: #38003c;
    }
    .subheader {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(
    '<p class="main-header" style="color:white; font-size:50px; font-weight:bold;">⚽ Premier League Media Sentiment Tracker</p>',
    unsafe_allow_html=True
)
st.markdown('<p class="subheader">Real-time analysis from Google News, BBC Sport & Sky Sports</p>', unsafe_allow_html=True)
st.markdown("---")

# Connect to Firestore using Streamlit secrets
@st.cache_resource
def get_db():
    """Initialize Firestore client with credentials from Streamlit secrets"""
    try:
        # Load credentials from Streamlit secrets (TOML format)
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        
        # Initialize Firestore client WITH the credentials
        return firestore.Client(
            credentials=credentials, 
            project=st.secrets["gcp_service_account"]["project_id"]
        )
    except Exception as e:
        st.error(f"Failed to initialize Firestore: {e}")
        raise

db = get_db()

# Fetch data
@st.cache_data(ttl=300)
def load_data(days=14):
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    docs = db.collection('team_sentiment')\
        .where('timestamp', '>=', cutoff_date)\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(1000)\
        .stream()
    
    data = []
    for doc in docs:
        d = doc.to_dict()
        data.append(d)
    
    return pd.DataFrame(data)

# Sidebar
st.sidebar.header("⚙️ Filters & Settings")

days_filter = st.sidebar.slider(
    "📅 Days of data to show",
    min_value=1,
    max_value=30,
    value=14
)

sentiment_filter = st.sidebar.radio(
    "😊 Filter by sentiment",
    ["All", "Positive (>0)", "Negative (<0)", "Neutral (≈0)"]
)

# Load data
try:
    with st.spinner("Loading data from Firestore..."):
        df = load_data(days=days_filter)
    
    if df.empty:
        st.warning("⏳ No data yet. The Cloud Function needs to run at least once.")
        st.info("""
        **Next steps:**
        1. Trigger your Cloud Function manually or wait for scheduled run
        2. Check Firestore console to verify data is being stored
        3. Refresh this dashboard
        """)
        st.stop()
    
    # Apply sentiment filter
    if sentiment_filter == "Positive (>0)":
        df = df[df['avg_sentiment'] > 0]
    elif sentiment_filter == "Negative (<0)":
        df = df[df['avg_sentiment'] < 0]
    elif sentiment_filter == "Neutral (≈0)":
        df = df[df['avg_sentiment'].between(-0.1, 0.1)]
    
    # Get latest sentiment for each team
    latest_sentiment = df.sort_values('timestamp').groupby('team').last().reset_index()
    latest_sentiment = latest_sentiment.sort_values('avg_sentiment', ascending=False)
    
    # === OVERVIEW METRICS ===
    st.subheader("📊 Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🏆 Teams Tracked", len(latest_sentiment))
    
    with col2:
        if not latest_sentiment.empty:
            most_positive = latest_sentiment.iloc[0]
            st.metric(
                "😊 Most Positive",
                most_positive['team'],
                delta=f"+{most_positive['avg_sentiment']:.2f}"
            )
    
    with col3:
        if not latest_sentiment.empty:
            most_negative = latest_sentiment.iloc[-1]
            st.metric(
                "😔 Most Negative",
                most_negative['team'],
                delta=f"{most_negative['avg_sentiment']:.2f}"
            )
    
    with col4:
        avg_sentiment = latest_sentiment['avg_sentiment'].mean()
        st.metric("📈 League Average", f"{avg_sentiment:.2f}")
    
    with col5:
        total_articles = df['article_count'].sum()
        st.metric("📝 Total Articles", f"{total_articles:,}")
    
    st.markdown("---")
    
    # === SENTIMENT RANKINGS ===
    st.subheader("🏅 Current Sentiment Rankings")
    
    colors = ['#00D9A3' if x > 0.1 else '#FF4B4B' if x < -0.1 else '#FFA500' 
              for x in latest_sentiment['avg_sentiment']]
    
    fig_bar = go.Figure()
    
    fig_bar.add_trace(go.Bar(
        y=latest_sentiment['team'],
        x=latest_sentiment['avg_sentiment'],
        orientation='h',
        marker=dict(color=colors),
        text=latest_sentiment['avg_sentiment'].round(3),
        textposition='outside'
    ))
    
    fig_bar.update_layout(
        title="Team Sentiment Scores (Latest)",
        xaxis_title="Sentiment Score",
        yaxis_title="",
        height=max(600, len(latest_sentiment) * 30),
        showlegend=False,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    fig_bar.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.3)
    
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # === TEAM COMPARISON ===
    st.subheader("📈 Team Sentiment Trends")

    all_teams = sorted(df['team'].unique())
    default_teams = latest_sentiment.head(6)['team'].tolist()

    selected_teams = st.multiselect(
        "Select teams to compare",
        options=all_teams,
        default=default_teams
    )

    if selected_teams:
        team_df = df[df['team'].isin(selected_teams)].copy()
        team_df['timestamp'] = pd.to_datetime(team_df['timestamp'])
        team_df = team_df.sort_values('timestamp')
        
        # Check if we have enough data points
        unique_times = team_df['timestamp'].nunique()
        
        if unique_times < 2:
            st.warning(f"⚠️ Only {unique_times} data point available. Need at least 2 time periods to show trends.")
            st.info("""
            **To see trend charts:**
            - Wait 12 hours for the next scheduled run
            - Or manually trigger the function again: `Invoke-WebRequest -Uri "YOUR_URL"`
            - Need at least 2-3 data collections from different times
            """)
            
            # Show current values instead
            st.subheader("Current Sentiment Values")
            current_df = team_df.groupby('team')['avg_sentiment'].last().reset_index()
            current_df = current_df.sort_values('avg_sentiment', ascending=False)
            
            fig_bar = px.bar(
                current_df,
                x='team',
                y='avg_sentiment',
                color='avg_sentiment',
                color_continuous_scale=['red', 'yellow', 'green'],
                title='Current Sentiment Scores'
            )
            fig_bar.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        else:
            # Show trend line chart
            fig_line = px.line(
                team_df,
                x='timestamp',
                y='avg_sentiment',
                color='team',
                title=f'Sentiment Over Time ({unique_times} data points)',
                labels={'avg_sentiment': 'Sentiment Score', 'timestamp': 'Time'},
                markers=True
            )
            
            # Format x-axis based on data span
            time_span = (team_df['timestamp'].max() - team_df['timestamp'].min()).total_seconds()
            
            if time_span < 86400:  # Less than 1 day - show hours
                fig_line.update_xaxes(tickformat='%I:%M %p')
            elif time_span < 604800:  # Less than 1 week - show days
                fig_line.update_xaxes(tickformat='%b %d')
            else:  # More than 1 week - show dates
                fig_line.update_xaxes(tickformat='%b %d')
            
            fig_line.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.3, annotation_text="Neutral")
            fig_line.update_layout(
                height=500,
                hovermode='x unified',
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
            )
            
            st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")
    
    # === KEY TOPICS ===
    st.subheader("🔑 Key Topics & Entities")
    
    if 'key_topics' in df.columns and selected_teams:
        for team in selected_teams:
            team_latest = df[df['team'] == team].sort_values('timestamp').iloc[-1]
            
            if 'key_topics' in team_latest and team_latest['key_topics']:
                with st.expander(f"🔍 {team} - Recent Topics"):
                    topics = team_latest['key_topics']
                    
                    if topics:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write("**Topic**")
                        with col2:
                            st.write("**Type**")
                        with col3:
                            st.write("**Relevance**")
                        
                        st.markdown("---")
                        
                        for topic in topics:
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.write(topic['name'])
                            with col2:
                                st.write(topic['type'])
                            with col3:
                                st.write(f"{topic['salience']:.1%}")
                    else:
                        st.write("No key topics extracted")
    
    st.markdown("---")
    
    # === AI SUMMARY ===
    st.subheader("📋 AI-Generated Summary Report")

    if st.button("Generate AI Summary for Selected Teams"):
        summary_text = f"**Premier League Media Sentiment Analysis**\n\n"
        summary_text += f"*Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}*\n\n---\n\n"
        
        for team in selected_teams:
            team_df = df[df['team'] == team].sort_values('timestamp')
            if team_df.empty:
                continue
            
            latest = team_df.iloc[-1]
            
            # Determine sentiment category and explanation
            score = latest['avg_sentiment']
            
            if score > 0.15:
                emoji, label = "🟢", "very positive"
                explanation = "strong performances, victories, and positive developments"
            elif score > 0.05:
                emoji, label = "🟢", "positive"
                explanation = "good form, favorable results, or promising developments"
            elif score < -0.15:
                emoji, label = "🔴", "very negative"
                explanation = "poor results, defensive struggles, managerial pressure, or off-field controversies"
            elif score < -0.05:
                emoji, label = "🔴", "negative"
                explanation = "disappointing performances, losses, or tactical concerns"
            else:
                emoji, label = "🟡", "neutral"
                explanation = "balanced coverage without strong positive or negative themes"
            
            summary_text += f"### {emoji} {team}\n\n"
            
            # Add context from entities if available
            has_entities = 'key_topics' in latest and latest['key_topics'] and len(latest['key_topics']) > 0
            
            if has_entities:
                topics = [t['name'] for t in latest['key_topics'][:3]]
                topic_text = ', '.join(topics[:-1]) + f", and {topics[-1]}" if len(topics) > 1 else topics[0]
                
                summary_text += f"{team} is experiencing {label} media coverage ({score:.2f}), "
                summary_text += f"with recent focus on {topic_text}. Coverage suggests {explanation}. "
            else:
                summary_text += f"{team} shows {label} sentiment ({score:.2f}), indicating {explanation}. "
            
            # Trend analysis
            if len(team_df) >= 3:
                recent_avg = team_df.tail(3)['avg_sentiment'].mean()
                older_avg = team_df.head(3)['avg_sentiment'].mean()
                change = recent_avg - older_avg
                
                if change > 0.1:
                    summary_text += f"Media perception has improved significantly (+{change:.2f}). "
                elif change > 0.03:
                    summary_text += f"Sentiment trending more positive recently. "
                elif change < -0.1:
                    summary_text += f"Coverage has turned sharply more critical ({change:.2f}). "
                elif change < -0.03:
                    summary_text += f"Media tone has worsened in recent reports. "
            
            summary_text += f"Analysis based on {team_df['article_count'].sum()} articles.\n\n---\n\n"
        
        # Overall insights
        if len(selected_teams) > 1:
            summary_text += "### League Overview\n\n"
            avg_all = df[df['team'].isin(selected_teams)].groupby('team').last()['avg_sentiment'].mean()
            summary_text += f"Average media sentiment: {avg_all:.2f}\n\n"
        
        st.markdown(summary_text)
        
        st.download_button(
            label="📥 Download AI Summary",
            data=summary_text,
            file_name=f"sentiment_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )
    
    # === DATA SOURCES ===
    st.subheader("📰 Data Sources Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'sources' in df.columns:
            all_sources = []
            for sources in df['sources']:
                if isinstance(sources, list):
                    all_sources.extend(sources)
            
            if all_sources:
                source_counts = pd.Series(all_sources).value_counts()
                
                fig_sources = px.pie(
                    values=source_counts.values,
                    names=source_counts.index,
                    title='Articles by Source'
                )
                st.plotly_chart(fig_sources, use_container_width=True)
    
    with col2:
        articles_per_team = df.groupby('team')['article_count'].sum().sort_values(ascending=False).head(10)
        
        fig_articles = px.bar(
            x=articles_per_team.values,
            y=articles_per_team.index,
            orientation='h',
            title='Top 10 Teams by Article Count',
            labels={'x': 'Total Articles', 'y': ''},
            color=articles_per_team.values,
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_articles, use_container_width=True)
    
    st.markdown("---")
    
    # === SENTIMENT DISTRIBUTION ===
    st.subheader("📊 Sentiment Distribution")
    
    fig_hist = px.histogram(
        latest_sentiment,
        x='avg_sentiment',
        nbins=20,
        title='Distribution of Team Sentiments',
        labels={'avg_sentiment': 'Sentiment Score'},
        color_discrete_sequence=['#667eea']
    )
    
    fig_hist.add_vline(x=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_hist, use_container_width=True)
    
    st.markdown("---")
    
    # === RECENT DATA TABLE ===
    st.subheader("📋 Recent Analysis Results")
    
    available_cols = ['team', 'avg_sentiment', 'article_count', 'sources', 'timestamp']
    show_cols = st.multiselect(
        "Select columns to display",
        options=available_cols,
        default=available_cols
    )
    
    display_df = df[show_cols].copy()
    display_df = display_df.sort_values('timestamp', ascending=False).head(100)
    
    if 'timestamp' in display_df.columns:
        display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Full Dataset (CSV)",
        data=csv,
        file_name=f"premier_league_sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.info("""
    **Troubleshooting:**
    - Make sure your GCP credentials are properly set in Streamlit Secrets
    - Verify your Firestore database is set up correctly
    - Check that the Cloud Function has run at least once
    """)
    
    with st.expander("Show full error details"):
        st.code(str(e))
        import traceback
        st.code(traceback.format_exc())

# === SIDEBAR INFO ===
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔄 Refresh Data")
if st.sidebar.button("Refresh Now"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("""
### ℹ️ About

**Data Sources:**
- 📰 Google News
- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 BBC Sport
- 📺 Sky Sports

**Analysis:**
- Google Cloud NLP API
- Sentiment scoring (-1 to +1)
- Entity extraction

**Technology:**
- Cloud Functions
- Firestore Database
- Streamlit Dashboard

**Project:**
IST 615 - Syracuse University

---
Made with ❤️ and ☁️
""")