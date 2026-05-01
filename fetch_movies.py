import requests
import json
import os
import time
from datetime import datetime
from tqdm import tqdm

API_KEY = os.environ['TMDB_API_KEY']
BASE_URL = "https://api.themoviedb.org/3"

# اطمینان از وجود پوشه data
os.makedirs("data", exist_ok=True)

def fetch_with_retry(url, params, max_retries=3):
    """درخواست با قابلیت تکرار در صورت خطا"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Too Many Requests
                wait_time = 60 * (attempt + 1)
                print(f"Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Error {response.status_code}: {response.text[:200]}")
                time.sleep(5)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(10)
    return None

def get_movies_by_year(year, min_vote=5.0):
    """دریافت فیلم‌های یک سال خاص با امتیاز بالاتر از min_vote"""
    movies = []
    page = 1
    
    print(f"Fetching movies from {year} (vote > {min_vote})...")
    
    while True:
        params = {
            'api_key': API_KEY,
            'language': 'en-US',
            'sort_by': 'vote_count.desc',
            'primary_release_year': year,
            'vote_average.gte': min_vote,
            'page': page
        }
        
        data = fetch_with_retry(f"{BASE_URL}/discover/movie", params)
        
        if not data or not data.get('results'):
            break
            
        for movie in tqdm(data['results'], desc=f"Year {year} - Page {page}"):
            # دریافت جزئیات کامل هر فیلم
            movie_id = movie['id']
            details = fetch_with_retry(f"{BASE_URL}/movie/{movie_id}", {
                'api_key': API_KEY,
                'language': 'en-US',
                'append_to_response': 'credits,keywords,recommendations,similar,videos,images,external_ids,release_dates,translations'
            })
            
            if details:
                movies.append(details)
            
            # تاخیر برای جلوگیری از Rate Limit
            time.sleep(0.2)
        
        page += 1
        if page > data.get('total_pages', 0):
            break
    
    return movies

def main():
    start_year = 1990
    end_year = 2026
    
    all_data = {}
    
    for year in range(start_year, end_year + 1):
        print(f"\n{'='*50}")
        print(f"Processing year {year}")
        print(f"{'='*50}")
        
        movies = get_movies_by_year(year, min_vote=5.0)
        
        # ساخت ساختار دیتا برای هر سال
        year_data = {
            "metadata": {
                "year": year,
                "total_movies": len(movies),
                "extraction_date": datetime.now().isoformat(),
                "source": "TMDB Complete API"
            },
            "movies": movies
        }
        
        # ذخیره در فایل JSON
        output_file = f"data/movies_{year}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(year_data, f, ensure_ascii=False, indent=2)
        
        # گزارش حجم فایل
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # تبدیل به مگابایت
        print(f"✅ Saved {len(movies)} movies to {output_file} ({file_size:.2f} MB)")
        
        all_data[year] = len(movies)
    
    # ذخیره فایل ایندکس (لیست تمام سال‌ها)
    index_data = {
        "metadata": {
            "total_years": len(all_data),
            "total_movies": sum(all_data.values()),
            "extraction_date": datetime.now().isoformat()
        },
        "years": all_data
    }
    
    with open("data/index.json", 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print("✅ ALL DONE!")
    print(f"{'='*50}")
    print(f"Total movies fetched: {sum(all_data.values())}")
    print(f"Total years: {len(all_data)}")

if __name__ == "__main__":
    main()
