"""
Data sources for fan sentiment analysis using RSS feeds
No authentication required - works immediately!
"""

import feedparser
import time

def fetch_google_news(team_name, limit=15):
    """
    Fetch news articles from Google News RSS
    100% reliable, no API key needed
    """
    try:
        # Format search query
        search_query = team_name.replace(' ', '+') + '+Premier+League'
        url = f'https://news.google.com/rss/search?q={search_query}&hl=en-US&gl=GB&ceid=GB:en'
        
        print(f"Fetching Google News for {team_name}...")
        print(f"URL: {url}")
        
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
                
                posts.append({
                    'text': text,
                    'source': 'BBC Sport',
                    'published': entry.get('published', ''),
                    'link': entry.get('link', '')
                })
            
            print(f"✓ Found {len(posts)} BBC Sport articles")
        
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
                
                posts.append({
                    'text': text,
                    'source': 'Sky Sports',
                    'published': entry.get('published', ''),
                    'link': entry.get('link', '')
                })
            
            print(f"✓ Found {len(posts)} Sky Sports articles")
        
        return posts
        
    except Exception as e:
        print(f"✗ Error fetching Sky Sports: {str(e)}")
        return []


def filter_posts_by_team(posts, team_name, team_variations):
    """
    Filter articles that mention the team
    """
    relevant_posts = []
    
    for post in posts:
        text_lower = post['text'].lower()
        
        # Check if any team variation is mentioned
        if any(variation.lower() in text_lower for variation in team_variations):
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
    
    # Source 1: Google News (team-specific)
    print("\n[1/3] Google News (team-specific)...")
    google_posts = fetch_google_news(team_name, limit=10)
    all_posts.extend(google_posts)
    time.sleep(1)  # Be polite
    
    # Source 2: BBC Sport (filter for team)
    print("\n[2/3] BBC Sport Premier League...")
    bbc_posts = fetch_bbc_sport_news(limit=20)
    filtered_bbc = filter_posts_by_team(bbc_posts, team_name, team_variations)
    print(f"  → Filtered to {len(filtered_bbc)} relevant articles")
    all_posts.extend(filtered_bbc)
    time.sleep(1)
    
    # Source 3: Sky Sports (filter for team)
    print("\n[3/3] Sky Sports...")
    sky_posts = fetch_sky_sports_news()
    filtered_sky = filter_posts_by_team(sky_posts, team_name, team_variations)
    print(f"  → Filtered to {len(filtered_sky)} relevant articles")
    all_posts.extend(filtered_sky)
    time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"✓ Total articles for {team_name}: {len(all_posts)}")
    print(f"  - Google News: {len(google_posts)}")
    print(f"  - BBC Sport: {len(filtered_bbc)}")
    print(f"  - Sky Sports: {len(filtered_sky)}")
    print(f"{'='*60}\n")
    
    return all_posts