from urllib.parse import urlparse

from django.db import models

# Create your models here.
from django.db.models import Count

from trendapp.models import Tweet, User, Feed, TweetManager


class ExModel(models.Model):
    class Meta:
        abstract = True

    def get_text(self):
        pass

    def for_date_range(self, start, end=None):
        pass


class TweetExManager(TweetManager):
    # def get_queryset(self):
    #     return super().get_queryset().exclude(tweetex__isnull=True)
    pass


class TweetEx(Tweet, ExModel):
    objects = TweetExManager()


class TextEx(models.Model):
    content = models.TextField()
    name = models.CharField(unique=True, max_length=255)


class UserExManager(models.Manager):
    def top_tweeters(self, cutoff=3000):
        users = list(self.annotate(num_tweets=Count("tweet")).filter(num_tweets__gte=cutoff))
        return users

    def for_names(self, names):
        return self.filter(screen_name__in=names)


class UserEx(User):
    objects = UserExManager()
