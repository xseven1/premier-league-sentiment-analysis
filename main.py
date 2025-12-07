"""
Premier League Sentiment Tracker - Cloud Function
Analyzes sentiment from multiple news RSS feeds with entity extraction
"""

import functions_framework
from google.cloud import language_v1
from google.cloud import firestore
from datetime import datetime
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
        
        # Filter out generic/unhelpful entities
        generic_terms = {
            team_name.lower(), 'premier league', 'epl', 'football', 'soccer', 
            'match', 'game', 'team', 'club', 'player', 'manager', 'coach',
            # Add all team names
            'manchester city', 'arsenal', 'liverpool', 'chelsea', 'manchester united',
            'tottenham', 'newcastle', 'brighton', 'aston villa', 'west ham',
            'man city', 'man united', 'man utd', 'spurs'
        }
        
        entities = []
        for entity in response.entities[:10]:  # Check more entities
            name_lower = entity.name.lower()
            
            # Skip if generic or too short
            if name_lower in generic_terms or len(entity.name) < 4:
                continue
                
            # Only include if meaningful (person, event, or specific topic)
            if entity.salience > 0.02:  # Higher threshold
                entities.append({
                    'name': entity.name,
                    'type': str(entity.type_),
                    'salience': round(entity.salience, 3)
                })
            
            if len(entities) >= 3:  # Limit to top 3 meaningful entities
                break
        
        print(f"   ✓ Found {len(entities)} meaningful entities")
        return entities
        
    except Exception as e:
        print(f"Entity extraction error: {e}")
        return []


@functions_framework.http
def sentiment_tracker(request):
    """
    Main Cloud Function entry point
    Fetches news and analyzes sentiment for Premier League teams
    """
    print("=" * 70)
    print("🏆 PREMIER LEAGUE SENTIMENT ANALYSIS - NEWS SOURCES")
    print("=" * 70)
    
    # Initialize clients
    nlp_client = language_v1.LanguageServiceClient()
    db = firestore.Client()
    
    results = []
    
    # Process all 20 teams
    teams_to_process = PREMIER_LEAGUE_TEAMS
    
    print(f"\n📋 Processing ALL {len(teams_to_process)} Premier League teams")
    print()
    
    for team_name, team_variations in teams_to_process.items():
        try:
            print(f"\n{'🔹'*35}")
            print(f"⚽ {team_name}")
            print(f"{'🔹'*35}")
            
            # Fetch news from multiple RSS sources
            posts = fetch_combined_news(team_name, team_variations)
            
            if not posts:
                print(f"⚠️  No articles found for {team_name}")
                continue
            
            # Analyze sentiment for each article
            sentiments = []
            sources_used = set()
            
            print(f"\n📊 Analyzing sentiment...")
            
            for post in posts[:7]:  # Limit to 7 articles per team
                text = post['text']
                
                if len(text) < 30:
                    continue
                
                score = analyze_sentiment(text, nlp_client)
                
                if score is not None:
                    sentiments.append(score)
                    sources_used.add(post['source'])
            
            # Store results if we have data
            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)
                
                # Generate entity summary
                print(f"   🔍 Extracting entities...")
                entities = generate_team_summary(posts, team_name, nlp_client)
                print(f"   ✓ Found {len(entities)} entities")
                
                result = {
                    'team': team_name,
                    'avg_sentiment': round(avg_sentiment, 3),
                    'article_count': len(sentiments),
                    'sources': list(sources_used),
                    'key_topics': entities,
                    'timestamp': datetime.utcnow(),
                    'league': 'Premier League',
                    'data_type': 'News Sentiment'
                }
                
                # Save to Firestore
                db.collection('team_sentiment').add(result)
                results.append(result)
                
                # Log result
                sentiment_emoji = "😊" if avg_sentiment > 0.1 else "😔" if avg_sentiment < -0.1 else "😐"
                sentiment_label = "POSITIVE" if avg_sentiment > 0.1 else "NEGATIVE" if avg_sentiment < -0.1 else "NEUTRAL"
                
                print(f"\n✅ {team_name}: {avg_sentiment:.3f} {sentiment_emoji} ({sentiment_label})")
                print(f"   📝 Analyzed {len(sentiments)} articles")
                print(f"   📰 Sources: {', '.join(sources_used)}")
                if entities:
                    print(f"   🔑 Key topics: {', '.join([e['name'] for e in entities[:3]])}")
            else:
                print(f"❌ {team_name}: No valid sentiment data")
            
        except Exception as e:
            print(f"❌ Error processing {team_name}: {e}")
            continue
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"✓ Teams processed: {len(results)}/{len(teams_to_process)}")
    print(f"✓ Total articles analyzed: {sum(r['article_count'] for r in results)}")
    
    if results:
        avg_all = sum(r['avg_sentiment'] for r in results) / len(results)
        print(f"✓ Average sentiment: {avg_all:.3f}")
    
    print("=" * 70)
    
    return {
        'status': 'success',
        'teams_processed': len(results),
        'total_articles': sum(r['article_count'] for r in results),
        'results': [{'team': r['team'], 'sentiment': r['avg_sentiment']} for r in results]
    }, 200