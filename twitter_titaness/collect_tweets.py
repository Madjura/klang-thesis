import datetime
import json
from collections import defaultdict

import twitter
from django.db import IntegrityError, transaction
from django.utils.timezone import make_aware

from titaness import setup

setup()
from trendapp.models import Tweet
from dataapp.models import TweetEx, UserEx
from twitter_titaness.secret import KEY, SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET


def collect_tweets(users_in, pr=None):
    if type(users_in) is str:
        users_in = [users_in]
    api = twitter.Api(consumer_key=KEY,
                      consumer_secret=SECRET,
                      access_token_key=ACCESS_TOKEN,
                      access_token_secret=ACCESS_TOKEN_SECRET,
                      sleep_on_rate_limit=True)
    for i, user in enumerate(users_in):
        if pr is not None:
            pr.set_progress(i + 1, len(users_in), description=f"Collecting new Tweets for user {user}.")
        tweets = []
        prev = None
        users_ids = []
        users = []
        user_ids_seen = defaultdict(lambda: False, {user.user_id: True for user in UserEx.objects.all()})
        id2tweets = defaultdict(lambda: list())
        try:
            while True:
                if prev is None:
                    data = api.GetUserTimeline(screen_name=user, count=200)
                else:
                    data = api.GetUserTimeline(screen_name=user, count=200, max_id=prev)
                prev = data[-1].id
                tweets.extend(data)
                if len(data) < 200:
                    # print("MAXIMUM: ", len(data))
                    break
        except twitter.TwitterError:
            pass
        tweets = [json.loads(x.AsJsonString()) for x in tweets]
        # store tweets or something
        for tweet in tweets:
            tweet = defaultdict(lambda: None, tweet)
            try:
                created_at = datetime.datetime.strptime(tweet["created_at"], "%m/%d/%Y, %H:%M:%S")
                make_aware(created_at)
            except ValueError:
                created_at = datetime.datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S %z %Y")
            tweet_obj = TweetEx(
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
            user_t = UserEx(
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
                users.append(user_t)
                user_ids_seen[user_id] = True
            id2tweets[user_id].append(tweet_obj)
        with transaction.atomic():
            for user_obj in users:
                user_obj.save()
        try:
            with transaction.atomic():
                for user_obj in users:
                    user_obj.save()
        except IntegrityError:
            print("---> IntegrityError while saving User instances to db. Possibly already saved to db <---")
        users = UserEx.objects.filter(user_id__in=users_ids)
        user2id = {user.user_id: user for user in users}
        tweets_store = []
        for user_id, tweets in id2tweets.items():
            for tweet in tweets:
                tweet.user = user2id[user_id]
                tweets_store.append(tweet)
        existing = set(TweetEx.objects.all().values_list("tweet_id", flat=True))
        create = [x for x in tweets_store if x.tweet_id not in existing]
        try:
            saved = 0
            for tweet in create:
                try:
                    tweet.save()
                    saved += 1
                except IntegrityError as e:
                    continue
            print(f"Saved {saved} (new) Tweets for user {user}.")
        except IntegrityError:
            print("---> IntegrityError while saving TweetEx instances to db. Possibly already saved to db <---")


def remove_tweets(users):
    if type(users) is str:
        users = [users]
    for user in users:
        UserEx.objects.filter(screen_name__iexact=user.lower()).delete()


if __name__ == "__main__":
    t = set(Tweet.objects.all())
    tex = set(TweetEx.objects.all())
    c = t.intersection(tex)
    cc = tex.intersection(t)
    # for tt in t:
    #     print(tt.tweet_ptr)
    collect_tweets(["NightwishBand"])
