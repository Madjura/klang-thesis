from django.db import models

# Create your models here.
from picklefield import PickledObjectField

from dataapp.models import TweetEx, TextEx
from trendapp.models import Tweet


class PreprocessedText(models.Model):
    """
    Represents the preprocessed texts of one user.

    !!! THIS IS FOR TWEETS ONLY !!!

    Renaming models is very annoying and not a good idea.
    """
    name = models.CharField(max_length=250)
    nouns_only = models.BooleanField(default=False)
    texts = PickledObjectField(null=True, blank=True)
    external = models.BooleanField(default=False)
    end = models.DateTimeField(null=True, blank=True)
    start = models.DateTimeField(null=True, blank=True)

    def get_tweets(self):
        try:
            return TweetEx.objects.filter(user__screen_name=self.name, created_at__gte=self.start,
                                          created_at__lte=self.end)
        except ValueError:
            return TweetEx.objects.none()

    class Meta:
        unique_together = ("name", "nouns_only", "external", "start", "end")


class PreprocessedDocument(models.Model):
    """
    Represents a single preprocessed external text.

    !!! THIS IS FOR EXTERNAL TEXTS ONLY !!!

    Renaming models is very annoying and not a good idea.
    """
    text = models.ForeignKey(TextEx, on_delete=models.CASCADE)
    nouns_only = models.BooleanField(default=False)
    texts = PickledObjectField(null=True, blank=True)


class ClusterResult(models.Model):
    """
    Represents the found clusters / keywords for texts of one user, in a given time range.
    """
    name = models.CharField(max_length=250)
    nouns_only = models.BooleanField(default=False)
    keywords = PickledObjectField(null=True, blank=True)
    vectorizer = PickledObjectField(null=True, blank=True)
    clusterer = PickledObjectField(null=True, blank=True)
    external = models.BooleanField(default=False)
    texts = models.ForeignKey(PreprocessedText, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("name", "nouns_only", "external", "texts")


class ClusterResultCombo(models.Model):
    """
    Represents the found clusters / keywords for
    """
    name = models.CharField(max_length=255, unique=True)
    nouns_only = models.BooleanField(default=False)
    keywords = PickledObjectField(null=True, blank=True)
    vectorizer = PickledObjectField(null=True, blank=True)
    clusterer = PickledObjectField(null=True, blank=True)


class KlangInput(models.Model):
    clusters = models.ManyToManyField(ClusterResult)
    model = PickledObjectField()
    name = models.CharField(max_length=250, unique=True)


class KlangInputCombo(models.Model):
    clusters = models.ManyToManyField(ClusterResultCombo)
    model = PickledObjectField()
    name = models.CharField(max_length=250, unique=True)


class KlangOutput(models.Model):
    klang_input = models.ForeignKey(KlangInput, on_delete=models.CASCADE)
    relations = PickledObjectField()


class KlangOutputCombo(models.Model):
    klang_input = models.ForeignKey(KlangInputCombo, on_delete=models.CASCADE)
    relations = PickledObjectField()
