import requests
from config_setting import Config

# Load Bearer Token from environment variable
BEARER_TOKEN = Config.TWITTER_BEARER_TOKEN

def search_tweets(query, max_results=10):
    return {}
    url = "https://api.x.com/2/tweets/search/recent"
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "author_id,created_at,geo,lang",
        "expansions": "geo.place_id",
        "place.fields": "full_name,country,country_code,geo,place_type"
    }

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        raise Exception(f"Error: {resp.status_code} {resp.text}")
    return resp.json()

if __name__ == "__main__":
    query = '(banjir OR flood OR 水灾 OR natural disaster) -is:retweet'
    tweets = search_tweets(query, max_results=20)
    print(tweets)
