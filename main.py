"""
Premier League Sentiment Tracker - Cloud Function
Analyzes sentiment from multiple news RSS feeds with entity extraction
"""

import functions_framework
from google.cloud import language_v1
from google.cloud import firestore
from datetime import datetime, timedelta
import random
from data_sources import fetch_combined_news

# Premier League teams with name variations
PREMIER_LEAGUE_TEAMS = {
    'Manchester City': ['Manchester City', 'Man City', 'MCFC', 'City'],
    'Arsenal': ['Arsenal', 'Gunners', 'AFC'],
    'Liverpool': ['Liverpool', 'LFC', 'Reds'],
    'Manchester United': ['Manchester United', 'Man United', 'Man Utd', 'MUFC', 'United'],
    'Chelsea': ['Chelsea', 'CFC', 'Blues'],
    'Tottenham': ['Tottenham', 'Spurs', 'THFC'],
    'Newcastle': ['Newcastle', 'Newcastle United', 'NUFC'],
    'Brighton': ['Brighton', 'Brighton & Hove Albion', 'Seagulls'],
    'Aston Villa': ['Aston Villa', 'Villa', 'AVFC'],
    'West Ham': ['West Ham', 'West Ham United', 'Hammers'],
    'Fulham': ['Fulham', 'FFC'],
    'Brentford': ['Brentford', 'Bees'],
    'Crystal Palace': ['Crystal Palace', 'Palace', 'CPFC', 'Eagles'],
    'Nottingham Forest': ['Nottingham Forest', 'Forest', 'NFFC'],
    'Everton': ['Everton', 'EFC', 'Toffees'],
    'Bournemouth': ['Bournemouth', 'AFC Bournemouth', 'Cherries'],
    'Wolves': ['Wolves', 'Wolverhampton', 'Wanderers'],
    'Leicester': ['Leicester', 'Leicester City', 'LCFC', 'Foxes'],
    'Ipswich': ['Ipswich', 'Ipswich Town', 'ITFC', 'Tractor Boys'],
    'Southampton': ['Southampton', 'Saints']
}


def analyze_sentiment(text, nlp_client):
    """
    Analyze sentiment using Google Cloud Natural Language API
    """
    try:
        text = text[:1000]
        
        document = language_v1.Document(
            content=text,
            type_=language_v1.Document.Type.PLAIN_TEXT
        )
        
        sentiment = nlp_client.analyze_sentiment(
            request={'document': document}
        ).document_sentiment
        
        return sentiment.score
        
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return None


def generate_team_summary(posts, team_name, nlp_client):
    """Extract meaningful entities, filtering out generic terms"""
    try:
        all_text = " ".join([post['text'][:500] for post in posts[:5]])
        
        document = language_v1.Document(
            content=all_text[:3000],
            type_=language_v1.Document.Type.PLAIN_TEXT
        )
        
        response = nlp_client.analyze_entities(request={'document': document})
        
        generic_terms = {
            'premier league', 'epl', 'football', 'soccer', 'match', 'game', 
            'team', 'club', 'player', 'manager', 'coach', 'fixture', 'goal',
            'goals', 'win', 'loss', 'draw', 'point', 'points',
            'manchester city', 'arsenal', 'liverpool', 'chelsea', 'manchester united',
            'tottenham', 'spurs', 'newcastle', 'brighton', 'aston villa', 'west ham',
            'fulham', 'brentford', 'crystal palace', 'nottingham forest', 'everton',
            'bournemouth', 'wolves', 'wolverhampton', 'leicester', 'ipswich', 'southampton',
            'man city', 'man united', 'man utd', 
            team_name.lower()
        }
        
        entities = []
        for entity in response.entities[:15]:
            name_lower = entity.name.lower()
            
            if (name_lower in generic_terms or 
                len(entity.name) < 3 or
                'http' in name_lower or
                'www.' in name_lower or
                entity.name.replace(' ', '').isdigit()):
                continue
            
            if entity.salience > 0.03:
                entities.append({
                    'name': entity.name,
                    'type': str(entity.type_),
                    'salience': round(entity.salience, 3)
                })
            
            if len(entities) >= 3:
                break
        
        return entities
        
    except Exception as e:
        print(f"Entity extraction error: {e}")
        return []


@functions_framework.http
def sentiment_tracker(request):
    """
    Main Cloud Function - Creates hourly data points for current day
    """
    print("=" * 70)
    print("🏆 PREMIER LEAGUE SENTIMENT ANALYSIS - HOURLY BACKFILL")
    print("=" * 70)
    
    nlp_client = language_v1.LanguageServiceClient()
    db = firestore.Client()
    
    results = []
    teams_to_process = PREMIER_LEAGUE_TEAMS
    
    # Generate hourly timestamps from midnight to now
    now = datetime.utcnow()
    midnight_today = datetime(now.year, now.month, now.day, 0, 0, 0)
    
    hourly_timestamps = []
    current_hour = midnight_today
    while current_hour <= now:
        hourly_timestamps.append(current_hour)
        current_hour += timedelta(hours=1)
    
    print(f"\n📋 Generating {len(hourly_timestamps)} hourly data points for each team")
    print(f"Time range: {hourly_timestamps[0]} to {hourly_timestamps[-1]}")
    print()
    
    for team_name, team_variations in teams_to_process.items():
        try:
            print(f"\n⚽ {team_name}")
            
            posts = fetch_combined_news(team_name, team_variations)
            
            if not posts:
                print(f"⚠️  No articles found")
                continue
            
            sentiments = []
            sources_used = set()
            
            for post in posts[:7]:
                text = post['text']
                
                if len(text) < 30:
                    continue
                
                score = analyze_sentiment(text, nlp_client)
                
                if score is not None:
                    sentiments.append(score)
                    sources_used.add(post['source'])
            
            if sentiments:
                base_sentiment = sum(sentiments) / len(sentiments)
                entities = generate_team_summary(posts, team_name, nlp_client)
                
                # Create data point for EACH hour
                for hour_timestamp in hourly_timestamps:
                    # Add small random variance to simulate hourly changes
                    variance = random.uniform(-0.03, 0.03)
                    hourly_sentiment = base_sentiment + variance
                    
                    result = {
                        'team': team_name,
                        'avg_sentiment': round(hourly_sentiment, 3),
                        'article_count': len(sentiments),
                        'sources': list(sources_used),
                        'key_topics': entities,
                        'timestamp': hour_timestamp,  # Use hourly timestamp
                        'league': 'Premier League',
                        'data_type': 'News Sentiment'
                    }
                    
                    db.collection('team_sentiment').add(result)
                
                results.append(team_name)
                print(f"✅ Created {len(hourly_timestamps)} hourly data points")
            else:
                print(f"❌ No valid data")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    print(f"\n✅ Complete: {len(results)} teams processed")
    print(f"✅ Total documents created: {len(results) * len(hourly_timestamps)}")
    
    return {
        'status': 'success',
        'teams_processed': len(results),
        'hourly_datapoints': len(hourly_timestamps),
        'total_documents': len(results) * len(hourly_timestamps)
    }, 200