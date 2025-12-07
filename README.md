# Premier League Fan Sentiment Tracker

Real-time sentiment analysis of Premier League fan reactions from Reddit and Twitter.

## Project Overview

This cloud-based analytics system:
- 📊 Fetches fan posts from Reddit and Twitter (no API keys needed!)
- 🧠 Analyzes sentiment using Google Cloud Natural Language API
- 💾 Stores results in Google Firestore
- 📈 Displays insights on an interactive Streamlit dashboard

## Architecture
```
Reddit + Twitter → Cloud Function → NLP API → Firestore → Dashboard
```

## Technologies

- **Google Cloud Platform:**
  - Cloud Functions (Serverless compute)
  - Natural Language API (Sentiment analysis)
  - Firestore (NoSQL database)
  - Cloud Scheduler (Automated triggers)
  
- **Data Sources:**
  - Reddit (via public JSON endpoints)
  - Twitter (via Nitter instances)
  
- **Dashboard:**
  - Streamlit (Python web framework)
  - Plotly (Interactive visualizations)

## Features

- ✅ 20 Premier League teams tracked
- ✅ Multi-source fan data (Reddit + Twitter)
- ✅ Real-time sentiment analysis
- ✅ Historical trend tracking
- ✅ Interactive dashboard
- ✅ No API keys required for data collection
- ✅ Stays within GCP free tier

## Setup Instructions

See deployment guide in main documentation.

## Course Information

**Course:** IST 615 - Cloud Management  
**Institution:** Syracuse University  
**Instructor:** Professor James Garrisi

## License

Educational use only.