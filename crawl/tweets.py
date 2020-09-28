import datetime
import os
from collections import defaultdict

import twitter
from dateutil.parser import parse as parse_datetime

# CONSTANTS
# DB_NAME = 'titaness_crawl2'
from titaness import setup

setup()
from trendapp.models import Tweet, User
from django.utils.timezone import make_aware
from titaness.settings import TWITTER_KEY, TWITTER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET


def normalize_datatime(s):
    try:
        return parse_datetime(s).strftime("%m/%d/%Y, %H:%M:%S")
    except Exception as e:
        print('ERROR: Could not parse "{}"'.format(s))
        print(e)
        return None


def key_func(item):
    return {'id': item['id']}


def process_item(item, col):
    item_title = item.get('text', '<untitled>')

    # if not already exists?
    if not col.find_one(key_func(item)):

        # normalize datetimes
        for k in ['created_at']:  # TODO: more?st
            if item.get(k, None) is not None:
                item[k] = normalize_datatime(item[k])

        # store
        col.insert(item)
        print('|    Stored new item: "{}"'.format(item_title))
        return True
    return False


def twitter_stuff(user, api, existing=None):
    retrieved = []
    prev = None
    try:
        while True:
            if prev is None:
                data = api.GetUserTimeline(screen_name=user, count=200)
            else:
                data = api.GetUserTimeline(screen_name=user, count=200, max_id=prev)
            prev = data[-1].id
            retrieved.extend(data)
            if len(data) < 200:
                print("MAXIMUM: ", len(data))
                break
    except twitter.TwitterError:
        pass
    users = []
    users_ids = []
    user_ids_seen = defaultdict(lambda: False, {user.user_id: True for user in User.objects.all()})
    id2tweets = defaultdict(lambda: list())

    for tweet in retrieved:
        if existing and tweet.id in existing:
            continue
        try:
            created_at = datetime.datetime.strptime(tweet.created_at, "%m/%d/%Y, %H:%M:%S")
            make_aware(created_at)
        except ValueError:
            created_at = datetime.datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y")
        tweet_obj = Tweet(
            tweet_id=tweet.id,
            created_at=created_at,
            text=tweet.text,
            truncated=tweet.truncated,
            source=tweet.source,
            in_reply_to_status_id=tweet.in_reply_to_status_id,
            in_reply_to_user_id=tweet.in_reply_to_user_id,
            in_reply_to_screen_name=tweet.in_reply_to_screen_name,
            retweet_count=tweet.retweet_count,
            favorite_count=tweet.favorite_count,
            lang=tweet.lang
        )
        d = tweet.user
        user_id = d.id
        user_created_at = datetime.datetime.strptime(d.created_at, "%a %b %d %H:%M:%S %z %Y")
        if not user_created_at.tzinfo:
            user_created_at = make_aware(user_created_at)
        user = User(
            user_id=user_id,
            name=d.name,
            screen_name=d.screen_name,
            location=d.location,
            description=d.description,
            url=d.url,
            protected=d.protected,
            followers_count=d.followers_count,
            friends_count=d.friends_count,
            listed_count=d.listed_count,
            created_at=user_created_at,
            favourites_count=d.favourites_count,
            geo_enabled=d.geo_enabled,
            verified=d.verified,
            statuses_count=d.statuses_count,
            lang=d.lang
        )
        users_ids.append(user_id)
        if not user_ids_seen[user_id]:
            users.append(user)
            user_ids_seen[user_id] = True
        id2tweets[user_id].append(tweet_obj)
    User.objects.bulk_create(users)

    users = User.objects.filter(user_id__in=users_ids)
    user2id = {user.user_id: user for user in users}
    create = []
    for user_id, tweets in id2tweets.items():
        for tweet in tweets:
            tweet.user = user2id[user_id]
            create.append(tweet)
    seen = set()
    create = [seen.add(x.tweet_id) or x for x in create if x.tweet_id not in seen]
    print(len(create))
    # Tweet.objects.bulk_create(create)


def crawl_and_store_tweets(pr=None):
    api = twitter.Api(consumer_key=TWITTER_KEY,
                      consumer_secret=TWITTER_SECRET,
                      access_token_key=TWITTER_ACCESS_TOKEN,
                      access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                      sleep_on_rate_limit=True)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets.txt"), "r") as f:
        users = f.readlines()
    # with open("stores.txt", "r") as f:
    #     users = f.readlines()

    existing = set(Tweet.objects.all().values_list("tweet_id", flat=True))
    for i, _user in enumerate(users):
        if pr is not None:
            pr.set_progress(i + 1, len(users), description=f"Collecting Tweets of user {_user}.")
        else:
            print(f"--> Processing user {_user} ({i + 1} out of {len(users)}) <--")
        twitter_stuff(_user, api, existing=existing)


if __name__ == '__main__':
    crawl_and_store_tweets()
