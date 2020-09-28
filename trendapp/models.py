import datetime
from collections import defaultdict

from django.db import models
from django.db.models import Q, Count


def month_last(day):
    next_month = day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    return next_month - datetime.timedelta(days=next_month.day)


def month_first(day):
    return day.replace(day=1)


class TweetManager(models.Manager):
    # TODO: 10 jan 2020 check if correct to comment this out or if it causes massive issues
    # def get_queryset(self):
    #     return super().get_queryset().exclude(tweetex__isnull=False)

    def for_more_than(self, limit):
        out = []
        users = list(User.objects.all())
        for user in users:
            tweets = self.filter(user=user).select_related("user")
            if len(tweets) >= limit:
                out.extend(tweets)
        return out

    def for_month(self, month, users=None):
        first = month_first(month)
        last = month_last(month)
        q = self.filter(Q(created_at__lte=last) & Q(created_at__gte=first))
        if users:
            q = q.filter(user__name__in=users)
        return q.select_related("user")

    def for_year(self, year, users=None):
        out = []
        for month in range(1, 13):
            if month < 10:
                month = f"0{month}"
            d = datetime.datetime.strptime(f"{month} {year}", "%m %Y")
            out.extend(self.for_month(d, users))
        return out

    def by_month(self, users=None):
        d = defaultdict(lambda: defaultdict(lambda: list()))
        q = self.all().select_related("user")
        if users:
            q = self.filter(user__name__in=users).select_related("user")
        for t in q:
            date = t.created_at.strftime("%m / %Y")
            month, year = date.split("/")
            d[year][month].append(t)
        return d

    def by_week_or_day(self, users=None, week=False):
        d = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list())))
        q = self.all().select_related("user")
        if users:
            q = self.filter(user__name__in=users).select_related("user")
        for t in q:
            date = t.created_at.strftime("%d / %m / %Y")
            day, month, year = date.split("/")
            if week:
                day = int(day) // 7
            d[year][month][day].append(t)
        return d

    def by_year(self, users=None):
        d = defaultdict(lambda: list())
        q = self.all().select_related("user")
        if users:
            q = self.filter(user__name__in=users).select_related("user")
        for t in q:
            year = t.created_at.strftime("%Y")
            d[year].append(t)
        return d


class FeedManager(models.Manager):
    def feed_items_per_channel(self):
        freq = defaultdict(int)
        for feed in self.all():
            freq[feed.channel_title] += 1
        return freq

    def by_month(self, by_channel=False):
        if by_channel:
            d = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list())))
        else:
            d = defaultdict(lambda: defaultdict(lambda: list()))
        q = self.filter(item_pubDate__isnull=False)
        for f in q:
            date = f.item_pubDate.strftime("%m / %Y")
            month, year = date.split("/")
            if by_channel:
                d[f.channel_title][year][month].append(f)
            else:
                d[year][month].append(f)
        return d


class UserManager(models.Manager):
    def top_tweeters(self, cutoff=3000):
        users = list(self.annotate(num_tweets=Count("tweet")).filter(num_tweets__gte=cutoff))
        return users

    def tweet_count_users(self, users):
        return [(x, x.num_tweets) for x in list(self.annotate(num_tweets=Count("tweet")).filter(name__in=users))]


class Tweet(models.Model):
    tweet_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(null=True)
    text = models.TextField(null=True)
    truncated = models.BooleanField(null=True)
    source = models.TextField(null=True)
    in_reply_to_status_id = models.IntegerField(null=True)
    in_reply_to_user_id = models.IntegerField(null=True)
    in_reply_to_screen_name = models.TextField(null=True)
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    retweet_count = models.IntegerField(null=True)
    favorite_count = models.IntegerField(null=True)
    lang = models.CharField(max_length=20, null=True)

    objects = TweetManager()


class StoreTweet(models.Model):
    tweet_id = models.IntegerField(unique=True)
    created_at = models.DateTimeField(null=True)
    text = models.TextField(null=True)
    truncated = models.BooleanField(null=True)
    source = models.TextField(null=True)
    in_reply_to_status_id = models.IntegerField(null=True)
    in_reply_to_user_id = models.IntegerField(null=True)
    in_reply_to_screen_name = models.TextField(null=True)
    user = models.ForeignKey("StoreUser", on_delete=models.CASCADE)
    retweet_count = models.IntegerField(null=True)
    favorite_count = models.IntegerField(null=True)
    lang = models.CharField(max_length=20, null=True)

    objects = TweetManager()


class Hashtag(models.Model):
    tweet = models.ForeignKey("Tweet", on_delete=models.CASCADE)
    beginning = models.IntegerField(null=True)
    end = models.IntegerField(null=True)
    tag = models.TextField(default="")


class Mention(models.Model):
    tweet = models.ForeignKey("Tweet", on_delete=models.CASCADE)
    beginning = models.IntegerField(null=True)
    end = models.IntegerField(null=True)
    screen_name = models.TextField(null=True)
    name = models.TextField(null=True)
    mention_id = models.IntegerField(null=True)


class TweetUrl(models.Model):
    tweet = models.ForeignKey("Tweet", on_delete=models.CASCADE)
    url = models.TextField(null=True)
    expanded_url = models.TextField(null=True)
    display_url = models.TextField(null=True)
    beginning = models.IntegerField(null=True)
    end = models.IntegerField(null=True)


class User(models.Model):
    user_id = models.IntegerField(unique=True, null=True)
    name = models.TextField(null=True)
    screen_name = models.TextField(null=True)
    location = models.TextField(null=True)
    description = models.TextField(null=True)
    url = models.TextField(null=True)
    protected = models.BooleanField(null=True)
    followers_count = models.IntegerField(null=True)
    friends_count = models.IntegerField(null=True)
    listed_count = models.IntegerField(null=True)
    created_at = models.DateTimeField(null=True)
    favourites_count = models.IntegerField(null=True)
    geo_enabled = models.BooleanField(null=True)
    verified = models.BooleanField(null=True)
    statuses_count = models.IntegerField(null=True)
    lang = models.CharField(max_length=20, null=True)

    objects = UserManager()

    def __str__(self):
        return self.screen_name


class StoreUser(models.Model):
    user_id = models.IntegerField(unique=True, null=True)
    name = models.TextField(null=True)
    screen_name = models.TextField(null=True)
    location = models.TextField(null=True)
    description = models.TextField(null=True)
    url = models.TextField(null=True)
    protected = models.BooleanField(null=True)
    followers_count = models.IntegerField(null=True)
    friends_count = models.IntegerField(null=True)
    listed_count = models.IntegerField(null=True)
    created_at = models.DateTimeField(null=True)
    favourites_count = models.IntegerField(null=True)
    geo_enabled = models.BooleanField(null=True)
    verified = models.BooleanField(null=True)
    statuses_count = models.IntegerField(null=True)
    lang = models.CharField(max_length=20, null=True)

    objects = UserManager()


class Feed(models.Model):
    # channel_link + item_guid
    channel_title = models.TextField(null=True)
    channel_link = models.TextField(null=True)
    channel_description = models.TextField(null=True)
    channel_language = models.CharField(max_length=20, null=True)
    channel_lastBuildDate = models.DateTimeField(null=True)
    item_title = models.TextField(null=True)
    item_link = models.TextField(null=True)
    item_description = models.TextField(null=True)
    item_pubDate = models.DateTimeField(null=True)
    item_guid = models.TextField(null=True, unique=True)
    topic = models.TextField(null=True)
    item_webpage = models.TextField(null=True)

    objects = FeedManager()


class FeedContent(models.Model):
    feed = models.OneToOneField("Feed", on_delete=models.CASCADE)
    title = models.TextField()
    content = models.TextField()


"""
from djongo import models
class Feeds(models.Model):
    _id = models.CharField(max_length=255, primary_key=True)
    channel_title = models.CharField(max_length=255)
    channel_link = models.CharField(max_length=255)
    channel_description = models.TextField()
    channel_language = models.CharField(max_length=30)
    channel_lastBuildDate = models.DateTimeField()
    item_title = models.TextField()
    item_link = models.TextField()
    item_description = models.TextField()
    item_pubDate = models.TextField()
    item_guid = models.TextField()
    topic = models.TextField()
    item_webpage = models.TextField()


class Tweets(models.Model):
    _id = models.CharField(max_length=20, primary_key=True)
    created_at = models.CharField(max_length=20)
    id = models.CharField(max_length=20)
    id_str = models.CharField(max_length=20)
    text = models.TextField()
    truncated = models.BooleanField()
    entities = models.TextField()
    source = models.TextField()
    in_reply_to_status_id = models.TextField()
    in_reply_to_status_id_str = models.TextField()
    in_reply_to_user_id = models.TextField()
    in_reply_to_user_id_str = models.TextField()
    in_reply_to_screen_name = models.TextField()
    user = models.TextField()
    geo = models.TextField()
    coordinates = models.TextField()
    place = models.TextField()
    contributors = models.TextField()
    is_quote_status = models.BooleanField()
    retweet_count = models.IntegerField()
    favorite_count = models.BooleanField()
    favorited = models.BooleanField()
    retweeted = models.BooleanField()
    possibly_sensitive = models.BooleanField()
    lang = models.CharField(max_length=30)
"""
