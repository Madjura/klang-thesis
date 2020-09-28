from django.db import models

# Create your models here.
from dataapp.models import TweetEx, TextEx
from trendapp.models import Tweet, Feed


class TweetIndexManager(models.Manager):
    def for_terms(self, terms, users=None):
        q = self.filter(term__in=terms)
        if users:
            q = q.select_related("tweet").filter(tweet__user__name__in=users)
        return q


class TweetIndex(models.Model):
    term = models.CharField(max_length=100)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE)
    bigram = models.BooleanField(default=False)
    lemmatized = models.BooleanField(default=False)

    objects = TweetIndexManager()

    class Meta:
        unique_together = ("term", "tweet", "bigram", "lemmatized")


class TweetNPIndex(models.Model):
    term = models.CharField(max_length=255)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, null=True, blank=True)
    frequency = models.IntegerField()
    tweet_user = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"TweetNPIndex: {self.term}: {self.frequency}"


class FeedNPIndex(models.Model):
    term = models.CharField(max_length=255)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, null=True, blank=True)
    frequency = models.IntegerField()
    feed_user = models.CharField(max_length=255, null=True, blank=True)


class TweetNPDateIndex(models.Model):
    term = models.CharField(max_length=255)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, null=True, blank=True)
    frequency = models.IntegerField()
    date = models.DateTimeField()


class FeedNPDateIndex(models.Model):
    term = models.CharField(max_length=255)
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE, null=True, blank=True)
    frequency = models.IntegerField()
    date = models.DateTimeField()


class TweetExIndex(models.Model):
    term = models.CharField(max_length=255)
    tweet = models.ForeignKey(TweetEx, on_delete=models.CASCADE)
    day = models.IntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    count = models.IntegerField()
    noun = models.BooleanField(default=False)

    class Meta:
        unique_together = ("term", "tweet", "day", "month", "year")


class TextExIndex(models.Model):
    term = models.CharField(max_length=255)
    text = models.ForeignKey(TextEx, on_delete=models.CASCADE)
    count = models.IntegerField()
    noun = models.BooleanField(default=False)

    class Meta:
        unique_together = ("term", "text")

