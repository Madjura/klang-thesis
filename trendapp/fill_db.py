import datetime
from collections import defaultdict

from django.utils.timezone import make_aware

from titaness import setup

setup()
from django.db import transaction, IntegrityError
from pymongo import MongoClient

from trendapp.models import Feed, Tweet, User, StoreTweet, StoreUser, Hashtag


def fill_feeds():
    existing = Feed.objects.all().values_list("item_guid", flat=True)
    existing = defaultdict(lambda: False, {guid: True for guid in existing})
    client = MongoClient()
    db = client.titaness_crawl2
    collection = db.feeds
    feeds = {}
    data = collection.find()
    duplicates = 0
    new = 0
    self_duplicates_count = 0
    self_duplicates = defaultdict(lambda: False)
    for feed in data:
        guid = feed["item_guid"]
        if existing[guid]:
            duplicates += 1
            continue
        else:
            new += 1
        if self_duplicates[guid]:
            _duplicate = feeds[guid]
            self_duplicates_count += 1
            continue
        feed = defaultdict(lambda: None, feed)
        date_val = feed["channel_lastBuildDate"]
        if date_val:
            date_val = date_val.replace("\n", "").replace("\t", "")
        try:
            build_date = datetime.datetime.strptime(date_val[:-6], "%a, %d %b %Y %H:%M:%S")
        except ValueError:
            build_date = datetime.datetime.strptime(date_val[:-4], "%a, %d %b %Y %H:%M:%S")
        except TypeError:
            build_date = None
        try:
            pub_date = datetime.datetime.strptime(feed["item_pubDate"], "%m/%d/%Y, %H:%M:%S")
        except TypeError:
            pub_date = None
        if build_date is not None and not build_date.tzinfo:
            build_date = make_aware(build_date)
        if pub_date is not None and not pub_date.tzinfo:
            pub_date = make_aware(pub_date)
        feed_obj = Feed(
            channel_title=feed["channel_title"],
            channel_link=feed["channel_link"],
            channel_description=feed["channel_description"],
            channel_language=feed["channel_language"],
            channel_lastBuildDate=build_date,
            item_title=feed["item_title"],
            item_link=feed["item_link"],
            item_description=feed["item_description"],
            item_pubDate=pub_date,
            item_guid=guid,
            topic=feed["topic"],
            item_webpage=feed["item_webpage"])
        feeds[guid] = feed_obj
        self_duplicates[guid] = True
    print(f"---> New: {new}, {duplicates} feeds already stored in db and thus skipped to avoid duplicates <---")
    try:
        with transaction.atomic():
            Feed.objects.bulk_create(feeds.values())
    except IntegrityError:
        print("---> IntegrityError while writing Feed data to db. Database probably already filled <---")


def fill_tweets(fill_hashtags=False):
    existing = Tweet.objects.all().values_list("tweet_id", flat=True)
    client = MongoClient()
    db = client.titaness_crawl2
    collection = db.tweets
    data = collection.find()
    users_ids = []
    users = []
    user_ids_seen = defaultdict(lambda: False, {user.user_id: True for user in User.objects.all()})
    id2tweets = defaultdict(lambda: list())
    existing_count = 0
    if fill_hashtags:
        data_fix = []
        ids = []
        tweet2id = {}
        create = []
        for tweet in data:
            ids.append(tweet["id"])
            data_fix.append(tweet)
        tweets = Tweet.objects.filter(tweet_id__in=ids)
        for tweet in tweets:
            tweet2id[tweet.tweet_id] = tweet
        for tweet in data_fix:
            hashtags = [x["text"] for x in tweet["hashtags"]]
            for tag in hashtags:
                try:
                    h = Hashtag(tweet=tweet2id[tweet["id"]], tag=tag)
                    create.append(h)
                except KeyError:
                    continue
        Hashtag.objects.bulk_create(create)
        return

    for i, tweet in enumerate(data):
        print(f"~~~ Processing Tweet {i + 1} ~~~")
        if tweet["id"] in existing:
            existing_count += 1
            print(f"# of already existing Tweets: {existing_count}")
            continue
        tweet = defaultdict(lambda: None, tweet)
        try:
            created_at = datetime.datetime.strptime(tweet["created_at"], "%m/%d/%Y, %H:%M:%S")
            make_aware(created_at)
        except ValueError:
            created_at = datetime.datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
        tweet_obj = Tweet(
            tweet_id=tweet["id"],
            created_at=created_at,
            text=tweet["text"],
            truncated=tweet["truncated"],
            source=tweet["source"],
            in_reply_to_status_id=tweet["in_reply_to_status_id"],
            in_reply_to_user_id=tweet["in_reply_to_user_id"],
            in_reply_to_screen_name=tweet["in_reply_to_screen_name"],
            retweet_count=tweet["retweet_count"],
            favorite_count=tweet["favourite_count"],
            lang=tweet["lang"]
        )
        d = tweet["user"]
        d = defaultdict(lambda: None, d)
        user_id = d["id"]
        user_created_at = datetime.datetime.strptime(d["created_at"], "%a %b %d %H:%M:%S %z %Y")
        if not user_created_at.tzinfo:
            user_created_at = make_aware(user_created_at)
        user = User(
            user_id=user_id,
            name=d["name"],
            screen_name=d["screen_name"],
            location=d["location"],
            description=d["description"],
            url=d["url"],
            protected=d["protected"],
            followers_count=d["followers_count"],
            friends_count=d["friends_count"],
            listed_count=d["listed_count"],
            created_at=user_created_at,
            favourites_count=d["favourites_count"],
            geo_enabled=d["geo_enabled"],
            verified=d["verified"],
            statuses_count=d["statuses_count"],
            lang=d["lang"]
        )
        users_ids.append(user_id)
        if not user_ids_seen[user_id]:
            users.append(user)
            user_ids_seen[user_id] = True
        id2tweets[user_id].append(tweet_obj)
    try:
        User.objects.bulk_create(users)
    except IntegrityError:
        print("---> IntegrityError while saving User instances to db. Possibly already saved to db <---")
    users = User.objects.filter(user_id__in=users_ids)
    user2id = {user.user_id: user for user in users}
    tweets_store = []
    for user_id, tweets in id2tweets.items():
        for tweet in tweets:
            tweet.user = user2id[user_id]
            tweets_store.append(tweet)
    existing = set(Tweet.objects.all().values_list("tweet_id", flat=True))
    create = [x for x in tweets_store if x.tweet_id not in existing]
    try:
        saved = 0
        for tweet in create:
            try:
                tweet.save()
                saved += 1
            except IntegrityError:
                continue
        print(saved)
    except IntegrityError:
        print("---> IntegrityError while saving Tweet instances to db. Possibly already saved to db <---")


def fill_tweets_stores():
    existing = StoreTweet.objects.all().values_list("tweet_id", flat=True)
    if existing.count() == 0:
        existing = []
    client = MongoClient()
    db = client.shop_experiment
    collection = db.tweets
    data = collection.find()
    users_ids = []
    users = []
    user_ids_seen = defaultdict(lambda: False, {user.user_id: True for user in User.objects.all()})
    id2tweets = defaultdict(lambda: list())
    existing_count = 0
    for i, tweet in enumerate(data):
        print(f"~~~ Processing Tweet {i + 1} ~~~")
        if tweet["id"] in existing:
            existing_count += 1
            print(f"# of already existing Tweets: {existing_count}")
            continue
        tweet = defaultdict(lambda: None, tweet)
        try:
            created_at = datetime.datetime.strptime(tweet["created_at"], "%m/%d/%Y, %H:%M:%S")
            make_aware(created_at)
        except ValueError:
            created_at = datetime.datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
        tweet_obj = StoreTweet(
            tweet_id=tweet["id"],
            created_at=created_at,
            text=tweet["text"],
            truncated=tweet["truncated"],
            source=tweet["source"],
            in_reply_to_status_id=tweet["in_reply_to_status_id"],
            in_reply_to_user_id=tweet["in_reply_to_user_id"],
            in_reply_to_screen_name=tweet["in_reply_to_screen_name"],
            retweet_count=tweet["retweet_count"],
            favorite_count=tweet["favourite_count"],
            lang=tweet["lang"]
        )
        d = tweet["user"]
        d = defaultdict(lambda: None, d)
        user_id = d["id"]
        user_created_at = datetime.datetime.strptime(d["created_at"], "%a %b %d %H:%M:%S %z %Y")
        if not user_created_at.tzinfo:
            user_created_at = make_aware(user_created_at)
        user = StoreUser(
            user_id=user_id,
            name=d["name"],
            screen_name=d["screen_name"],
            location=d["location"],
            description=d["description"],
            url=d["url"],
            protected=d["protected"],
            followers_count=d["followers_count"],
            friends_count=d["friends_count"],
            listed_count=d["listed_count"],
            created_at=user_created_at,
            favourites_count=d["favourites_count"],
            geo_enabled=d["geo_enabled"],
            verified=d["verified"],
            statuses_count=d["statuses_count"],
            lang=d["lang"]
        )
        users_ids.append(user_id)
        if not user_ids_seen[user_id]:
            users.append(user)
            user_ids_seen[user_id] = True
        id2tweets[user_id].append(tweet_obj)
    try:
        with transaction.atomic():
            StoreUser.objects.bulk_create(users)
    except IntegrityError:
        print("---> IntegrityError while saving User instances to db. Possibly already saved to db <---")
    users = StoreUser.objects.filter(user_id__in=users_ids)
    user2id = {user.user_id: user for user in users}
    tweets_store = []
    for user_id, tweets in id2tweets.items():
        for tweet in tweets:
            tweet.user = user2id[user_id]
            tweets_store.append(tweet)
    try:
        with transaction.atomic():
            StoreTweet.objects.bulk_create(tweets_store)
    except IntegrityError:
        print("---> IntegrityError while saving Tweet instances to db. Possibly already saved to db <---")


if __name__ == "__main__":
    fill_tweets(fill_hashtags=False)
    # fill_feeds()
    # fill_tweets_stores()
    # print(Tweet.objects.all().count())
    # print(Feed.objects.all().count())
    # print(Hashtag.objects.all().count())