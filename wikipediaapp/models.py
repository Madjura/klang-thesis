# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class CoN(models.Model):
    w1_id = models.PositiveIntegerField(primary_key=True)
    w2_id = models.PositiveIntegerField()
    freq = models.PositiveIntegerField(blank=True, null=True)
    sig = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'co_n'
        unique_together = (('w1_id', 'w2_id'),)


class CoS(models.Model):
    w1_id = models.PositiveIntegerField(primary_key=True)
    w2_id = models.PositiveIntegerField()
    freq = models.PositiveIntegerField(blank=True, null=True)
    sig = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'co_s'
        unique_together = (('w1_id', 'w2_id'),)


class InvSo(models.Model):
    so_id = models.PositiveIntegerField()
    s_id = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = 'inv_so'


class InvW(models.Model):
    w_id = models.PositiveIntegerField()
    s_id = models.PositiveIntegerField()
    pos = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = 'inv_w'


class Sentences(models.Model):
    s_id = models.AutoField(primary_key=True)
    sentence = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sentences'


class Sources(models.Model):
    so_id = models.AutoField(primary_key=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sources'


class Words(models.Model):
    w_id = models.AutoField(primary_key=True)
    word = models.CharField(max_length=255, blank=True, null=True)
    word_ci = models.CharField(max_length=255, blank=True, null=True)
    freq = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'words'
