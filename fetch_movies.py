import requests
import json
import os
import time
import sys
from datetime import datetime

# استفاده از Access Token
ACCESS_TOKEN = os.environ.get('TMDB_ACCESS_TOKEN')

if not ACCESS_TOKEN:
    print("❌ ERROR: TMDB_ACCESS_TOKEN not found in Secrets!")
    print("Please add your Access Token to GitHub Secrets as 'TMDB_ACCESS_TOKEN'")
    sys.exit(1)

# هدرهای درخواست
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json;charset=utf-8"
}

BASE_URL = "https://api.themoviedb.org/3"
os.makedirs("data", exist_ok=True)

# append_to_response (برای دریافت همه اطلاعات)
APPEND_TO_RESPONSE = "videos,images,credits,keywords,recommendations,similar,external_ids,release_dates,translations"

def fetch_with_retry(url, params, max_retries=3):
    """درخواست با قابلیت تکرار در صورت خطا"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print(f"❌ Authentication error! Check your Access Token!")
                sys.exit(1)
            elif response.status_code == 429:
                wait_time = 60 * (attempt + 1)
                print(f"⚠️ Rate limit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"⚠️ Error {response.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            time.sleep(10)
    return None

def get_movies_by_year(year, min_votes=100, min_rating=7.0, limit=500):
    """دریافت فیلم‌های یک سال خاص (مانند کد شما)"""
    movies = []
    page = 1
    
    print(f"\n📅 Fetching movies from {year} (votes >= {min_votes}, rating >= {min_rating})...")
    
    while page <= 25 and len(movies) < limit:
        params = {
            'primary_release_year': year,
            'sort_by': 'vote_average.desc',
            'vote_count.gte': min_votes,
            'vote_average.gte': min_rating,
            'include_adult': False,
            'page': page
        }
        
        data = fetch_with_retry(f"{BASE_URL}/discover/movie", params)
        
        if not data or not data.get('results'):
            break
        
        for movie in data['results']:
            if movie['id'] not in [m['id'] for m in movies]:
                movies.append(movie)
        
        print(f"   Page {page}: {len(data['results'])} movies (total: {len(movies)})")
        page += 1
        time.sleep(0.1)
    
    # محدود کردن به limit و مرتب‌سازی بر اساس امتیاز
    movies = sorted(movies, key=lambda x: x.get('vote_average', 0), reverse=True)[:limit]
    print(f"   ✅ Found {len(movies)} movies for {year}")
    return movies

def get_complete_movie_details(movie_id):
    """دریافت جزئیات کامل فیلم (مانند کد شما)"""
    params = {
        "append_to_response": APPEND_TO_RESPONSE,
        "language": "en-US"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/movie/{movie_id}",
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # اضافه کردن لینک‌های کامل تصاویر
            if data.get('poster_path'):
                data['poster_url'] = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
            if data.get('backdrop_path'):
                data['backdrop_url'] = f"https://image.tmdb.org/t/p/w1280{data['backdrop_path']}"
            
            # خلاصه‌سازی اطلاعات بازیگران
            if data.get('credits'):
                director = next((c['name'] for c in data['credits'].get('crew', []) if c['job'] == 'Director'), None)
                writer = next((c['name'] for c in data['credits'].get('crew', []) if c['job'] == 'Screenplay'), None)
                main_cast = [{'name': c['name'], 'character': c['character']} for c in data['credits'].get('cast', [])[:10]]
                
                data['credits_summary'] = {
                    'director': director,
                    'writer': writer,
                    'cast': main_cast,
                    'total_cast': len(data['credits'].get('cast', [])),
                    'total_crew': len(data['credits'].get('crew', []))
                }
            
            # خلاصه‌سازی ویدیوها
            if data.get('videos') and data.get('videos', {}).get('results'):
                data['videos_summary'] = [
                    {'name': v['name'], 'key': v['key'], 'type': v['type']}
                    for v in data['videos']['results'] if v['site'] == 'YouTube'
                ][:5]
            
            # خلاصه‌سازی keywords
            if data.get('keywords') and data.get('keywords', {}).get('keywords'):
                data['keywords_summary'] = [k['name'] for k in data['keywords']['keywords'][:15]]
            
            return data
        return {}
    except Exception as e:
        print(f"      ❌ Error getting details for movie {movie_id}: {e}")
        return {}

def main():
    start_year = 1990
    end_year = 2026
    min_rating = 6.0
    
    print("=" * 60)
    print("🎬 TMDB Movie Database Fetcher (Using Access Token)")
    print("=" * 60)
    print(f"Years: {start_year} to {end_year}")
    print(f"Minimum rating: {min_rating}")
    print("=" * 60)
    
    total_movies = 0
    stats = {'api_calls': 0}
    
    for year in range(start_year, end_year + 1):
        print(f"\n{'='*50}")
        print(f"📅 Processing year {year}")
        print(f"{'='*50}")
        
        # مرحله 1: دریافت لیست فیلم‌های سال
        movies = get_movies_by_year(year, min_votes=100, min_rating=min_rating, limit=500)
        
        # مرحله 2: دریافت جزئیات کامل هر فیلم
        detailed_movies = []
        total = len(movies)
        
        for i, movie in enumerate(movies, 1):
            print(f"   [{i}/{total}] Getting details: {movie.get('title', 'Unknown')[:50]}...")
            details = get_complete_movie_details(movie['id'])
            if details:
                detailed_movies.append(details)
                stats['api_calls'] += 1
            time.sleep(0.1)
        
        # ساخت ساختار دیتا برای هر سال
        year_data = {
            "metadata": {
                "year": year,
                "total_movies": len(detailed_movies),
                "min_rating": min_rating,
                "extraction_date": datetime.now().isoformat(),
                "source": "TMDB Complete API"
            },
            "movies": detailed_movies
        }
        
        # ذخیره در فایل JSON
        output_file = f"data/movies_{year}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(year_data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"   ✅ Saved {len(detailed_movies)} movies ({file_size:.2f} MB)")
        
        total_movies += len(detailed_movies)
    
    # ذخیره فایل ایندکس
    index_data = {
        "metadata": {
            "total_years": end_year - start_year + 1,
            "total_movies": total_movies,
            "total_api_calls": stats['api_calls'],
            "extraction_date": datetime.now().isoformat()
        }
    }
    
    with open("data/index.json", 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ ALL DONE!")
    print("=" * 60)
    print(f"Total movies: {total_movies}")
    print(f"Total API calls: {stats['api_calls']}")

if __name__ == "__main__":
    main()
