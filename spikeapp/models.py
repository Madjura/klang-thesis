from django.db import models

# Create your models here.
from picklefield import PickledObjectField

from dataapp.models import UserEx


class SpikeModel(models.Model):
    name = models.CharField(max_length=255, unique=True)
    reference = models.ManyToManyField(UserEx)

    def __str__(self):
        return self.name


class SpikeRange(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    scores = PickledObjectField()
    model = models.ForeignKey(SpikeModel, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("start", "end", "model")
