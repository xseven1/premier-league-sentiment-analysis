"""
Data sources for fan sentiment analysis using RSS feeds
No authentication required - works immediately!
"""

import feedparser
import time
from datetime import datetime, timedelta

def fetch_google_news(team_name, limit=15, days_back=None):
    """
    Fetch news articles from Google News RSS
    Can optionally fetch older articles for historical data
    """
    try:
        # Format search query
        search_query = team_name.replace(' ', '+') + '+Premier+League'
        
        # Add date range if specified (for historical backfill)
        if days_back:
            from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            search_query += f'+after:{from_date}'
        
        url = f'https://news.google.com/rss/search?q={search_query}&hl=en-US&gl=GB&ceid=GB:en'
        
        print(f"Fetching Google News for {team_name}...")
        
        # Parse RSS feed
        feed = feedparser.parse(url)
        
        posts = []
        
        if feed.entries:
            for entry in feed.entries[:limit]:
                # Combine title and summary
                text = entry.title
                if hasattr(entry, 'summary'):
                    text += ' ' + entry.summary
                
                posts.append({
                    'text': text,
                    'source': 'Google News',
                    'published': entry.get('published', ''),
                    'link': entry.get('link', '')
                })
            
            print(f"✓ Found {len(posts)} articles for {team_name}")
        else:
            print(f"⚠ No articles found for {team_name}")
        
        return posts
        
    except Exception as e:
        print(f"✗ Error fetching news for {team_name}: {str(e)}")
        return []


def fetch_bbc_sport_news(limit=20):
    """
    Fetch from BBC Sport Premier League RSS feed
    """
    try:
        url = 'https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml'
        
        print("Fetching from BBC Sport RSS...")
        feed = feedparser.parse(url)
        
        posts = []
        
        if feed.entries:
            for entry in feed.entries[:limit]:
                text = entry.title
                if hasattr(entry, 'summary'):
                    text += ' ' + entry.summary
                elif hasattr(entry, 'description'):
                    text += ' ' + entry.description
                
                posts.append({
                    'text': text,
                    'source': 'BBC Sport',
                    'published': entry.get('published', ''),
                    'link': entry.get('link', '')
                })
            
            print(f"✓ Found {len(posts)} BBC Sport articles")
        else:
            print(f"⚠ BBC Sport returned no articles")
        
        return posts
        
    except Exception as e:
        print(f"✗ Error fetching BBC Sport: {str(e)}")
        return []


def fetch_sky_sports_news():
    """
    Fetch from Sky Sports RSS feed
    """
    try:
        url = 'https://www.skysports.com/rss/12040'
        
        print("Fetching from Sky Sports RSS...")
        feed = feedparser.parse(url)
        
        posts = []
        
        if feed.entries:
            for entry in feed.entries[:20]:
                text = entry.title
                if hasattr(entry, 'summary'):
                    text += ' ' + entry.summary
                elif hasattr(entry, 'description'):
                    text += ' ' + entry.description
                
                posts.append({
                    'text': text,
                    'source': 'Sky Sports',
                    'published': entry.get('published', ''),
                    'link': entry.get('link', '')
                })
            
            print(f"✓ Found {len(posts)} Sky Sports articles")
        else:
            print(f"⚠ Sky Sports returned no articles")
        
        return posts
        
    except Exception as e:
        print(f"✗ Error fetching Sky Sports: {str(e)}")
        return []


def filter_posts_by_team(posts, team_name, team_variations):
    """
    Filter articles that mention the team
    Uses flexible matching - checks if ANY variation appears in text
    """
    relevant_posts = []
    
    for post in posts:
        text_lower = post['text'].lower()
        
        # Check if any team variation is mentioned
        # Also check for partial matches (e.g., "United" in "Manchester United")
        found = False
        for variation in team_variations:
            variation_lower = variation.lower()
            
            # Direct match or word boundary match
            if variation_lower in text_lower:
                # Avoid false positives (e.g., "United" matching "United States")
                # Check if it's a word boundary match
                words = text_lower.split()
                for word in words:
                    if variation_lower in word:
                        found = True
                        break
            
            if found:
                break
        
        if found:
            relevant_posts.append(post)
    
    return relevant_posts


def fetch_combined_news(team_name, team_variations):
    """
    Fetch news from multiple RSS sources and filter by team
    
    Args:
        team_name: Full team name (e.g., "Liverpool")
        team_variations: List of name variations (e.g., ["Liverpool", "LFC"])
    
    Returns:
        List of relevant news articles
    """
    all_posts = []
    
    print(f"\n{'='*60}")
    print(f"Collecting news for: {team_name}")
    print(f"{'='*60}")
    
    # Source 1: Google News (team-specific - most reliable)
    print("\n[1/3] Google News (team-specific)...")
    google_posts = fetch_google_news(team_name, limit=10)
    all_posts.extend(google_posts)
    time.sleep(1)  # Be polite
    
    # Source 2: BBC Sport (filter for team)
    print("\n[2/3] BBC Sport Premier League...")
    bbc_posts = fetch_bbc_sport_news(limit=20)
    if bbc_posts:
        filtered_bbc = filter_posts_by_team(bbc_posts, team_name, team_variations)
        print(f"  → Filtered to {len(filtered_bbc)} relevant articles")
        all_posts.extend(filtered_bbc)
    else:
        print(f"  → BBC Sport fetch failed, skipping")
    time.sleep(1)
    
    # Source 3: Sky Sports (filter for team)
    print("\n[3/3] Sky Sports...")
    sky_posts = fetch_sky_sports_news()
    if sky_posts:
        filtered_sky = filter_posts_by_team(sky_posts, team_name, team_variations)
        print(f"  → Filtered to {len(filtered_sky)} relevant articles")
        all_posts.extend(filtered_sky)
    else:
        print(f"  → Sky Sports fetch failed, skipping")
    time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"✓ Total articles for {team_name}: {len(all_posts)}")
    if google_posts:
        print(f"  - Google News: {len(google_posts)}")
    if bbc_posts:
        print(f"  - BBC Sport: {len([p for p in all_posts if p['source'] == 'BBC Sport'])}")
    if sky_posts:
        print(f"  - Sky Sports: {len([p for p in all_posts if p['source'] == 'Sky Sports'])}")
    print(f"{'='*60}\n")
    
    return all_posts