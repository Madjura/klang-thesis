# Generated by Django 3.0.2 on 2020-09-28 16:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('trendapp', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='TextEx',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='TweetEx',
            fields=[
                ('tweet_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='trendapp.Tweet')),
            ],
            options={
                'abstract': False,
            },
            bases=('trendapp.tweet', models.Model),
        ),
        migrations.CreateModel(
            name='UserEx',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='trendapp.User')),
            ],
            bases=('trendapp.user',),
        ),
    ]