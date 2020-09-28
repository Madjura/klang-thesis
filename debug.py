import datetime
import functools
import os
import pickle
from collections import defaultdict

import gensim as gensim
import pandas as pd
import requests
from django.db.models import Count
from django.db.models.functions import TruncMonth
from gensim import corpora, models
from pymongo import MongoClient
from scipy.spatial.distance import cosine

from common.text import get_spacy_model
from common.util import scale2range
from feature_extraction.scaffidi import feature_extraction_spike
from indexapp.models import TweetIndex, TweetExIndex
from thesaurus.similarity import _get_vector
from titaness import setup
from twitter_titaness.collect_tweets import collect_tweets

setup()
from trendapp.models import User, Tweet, Feed
from topicapp.models import SITRIExModel
from dataapp.models import UserEx, TweetEx


def preprocess(nlp, text):
    nlp = nlp(text)
    words = []
    for sent in nlp.sents:
        for word in sent:
            if not word.is_stop:
                words.append(word.lemma_)
    return words


def preprocess_all(nlp, texts):
    docs = nlp.pipe(texts, batch_size=1000)
    words_all = []
    for i, doc in enumerate(docs):
        print(f"--> Processing {i + 1} out of {len(texts)} <--")
        words = []
        for sent in doc.sents:
            for word in sent:
                if not word.is_stop:
                    if len(word.lemma_) > 2:
                        words.append(word.lemma_)
        words_all.append(words)
    return words_all


def foo2():
    client = MongoClient()
    db = client.titaness_data
    collection = db.feeds
    print(collection)


def dateFoo():
    foo = 'Thu, 11 Apr 2019 15:10:01 -0400'
    foo = foo.split(" -")[0]
    d = datetime.datetime.strptime(foo, "%a, %d %b %Y %H:%M:%S")
    print(d)


def tweets_per_user():
    users = list(User.objects.all())
    top_tweeters = []
    for user in users:
        tweets = list(Tweet.objects.filter(user=user)
                      .annotate(month=TruncMonth("created_at"))
                      # .values("month")
                      .annotate(c=Count("id"))
                      # .values("month", "c")
                      )
        tweets = sorted(tweets, key=lambda k: k.created_at)
        # if len(tweets) >= 500:
        #     print(user.name, len(tweets))
        top_tweeters.append((user, user.screen_name, len(tweets)))
    top_tweeters = sorted(top_tweeters, key=lambda k: k[1], reverse=True)
    return top_tweeters


def date_experiment():
    foo = "04 2017"
    users = ["London Business School", "CEIBS", "MIT Sloan School of Management"]
    d = datetime.datetime.strptime(foo, "%m %Y")
    print(d)
    tweets = list(Tweet.objects.for_month(d, users=users))
    print(list(tweets))


def print_unigrams():
    with open("/home/madjura/PycharmProjects/titaness/feature_extraction/scaffidi.p", "rb") as f:
        unigrams = pickle.load(f)
    unigrams = sorted(unigrams, key=lambda k: k[1])
    print(unigrams)


def print_bigrams():
    with open("/home/madjura/PycharmProjects/titaness/feature_extraction/scaffidi_bigrams.p", "rb") as f:
        bigrams = pickle.load(f)
    bigrams = sorted(bigrams, key=lambda k: k[1])
    print(bigrams)


def china():
    url = 'http://www.cuhk.edu.hk/english/features/wu_yilin.html'
    res = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8,de;q=0.7",
        "Accept-Encoding": ', '.join(('gzip', 'deflate')),
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": "1",
        "Cookie": "__nxquid=9hwwXQAAAAAi0zUwglIBKA==-1780015; __nxqsid=15571332000015"

    })
    content = res.content
    return content


def feed_stuff():
    d = Feed.objects.by_month(by_channel=True)
    print(d)


def calculate_gensim_corpus_feeds():
    feeds = Tweet.objects.filter(user__name="London Business School")
    # feeds = FeedContent.objects.filter(feed__channel_title="News In and Around CSD")
    texts = [x.text for x in feeds]
    # texts = [x.title for x in feeds]
    nlp = get_spacy_model(lang="en")
    text_data = preprocess_all(nlp, texts)
    dictionary = corpora.Dictionary(text_data)
    corpus = [dictionary.doc2bow(text) for text in text_data]
    tfidf = models.TfidfModel(corpus)
    corpus_tfidf = tfidf[corpus]
    # (26, '0.021*"nuclear" + 0.019*"philanthropy" + 0.008*"acquisition"')
    # ^ what?
    print("--> CALCULATING MODEL <--")
    ldamodel = gensim.models.ldamodel.LdaModel(corpus_tfidf, id2word=dictionary, num_topics=10, passes=10,
                                               iterations=100000000, minimum_probability=0.01)
    topics = ldamodel.print_topics(num_words=3)
    for topic in topics:
        print(topic)


def tweet_inheritance_experiment():
    t = Tweet.objects.for_more_than(10)
    print(t)


def rename_old_users():
    u = User.objects.all()
    n = set(u.values_list("screen_name", flat=True))
    for uu in u:
        uu.screen_name = uu.screen_name[:-4]
        uu.save()


def port_old_users_2_ex():
    u = tweets_per_user()
    relevant = []
    for i, (user, name, count) in enumerate(u):
        print(f"--> Processing user {i + 1} out of {len(u)} <--")
        if count > 100:
            relevant.append(name)
    # with open("RELEVANT.txt", "w") as f:
    #     f.write("\n".join(relevant))
    User.objects.all().delete()
    collect_tweets(relevant)


def sitri_exmodel():
    # SITRIExModel.objects.all().delete()
    SITRIExModel.create(True, "DEBUG")


def port2new():
    with open("RELEVANT.txt") as f:
        relevant = [x.strip() for x in f.readlines()]
    User.objects.all().delete()
    UserEx.objects.all().delete()
    collect_tweets(relevant)


def check_sitri():
    SITRIExModel.objects.all().delete()
    s = list(SITRIExModel.objects.filter(model_name="DEBUG"))
    print(s[0].initial)


def find_duplicate():
    a = UserEx.objects.all()
    foo = [x.screen_name for x in a]
    foo = sorted(foo)
    print(foo)


def spike_experiment():
    lbs = TweetEx.objects.filter(user__screen_name__iexact="lbs").order_by("-created_at")
    latest = list(lbs[:100])
    old = list(lbs[100:])
    latest_reference = TweetEx.objects.filter(created_at__lte=latest[0].created_at,
                                              created_at__gte=latest[-1].created_at)
    old_reference = TweetEx.objects.filter(created_at__lte=old[0].created_at, created_at__gte=old[-1].created_at)
    print(latest)
    scaff_latest = feature_extraction_spike(latest, latest_reference, min_length=0, nouns_only=True)
    scaff_new_mapping = {term: score for term, score in scaff_latest}
    scaff_old = feature_extraction_spike(old, old_reference, min_length=0, nouns_only=True)
    features_latest = set(x[0] for x in scaff_latest)
    features_old = set(x[0] for x in scaff_old)
    shared = features_latest.intersection(features_old)
    newcomers = [(term, scaff_new_mapping[term]) for term in features_latest.difference(features_old)]
    newcomers = sorted(newcomers, key=lambda k: k[1])

    rank_new = {term: i for i, (term, _score) in enumerate(scaff_latest)}
    rank_old = {term: i for i, (term, _score) in enumerate(scaff_old)}

    min_ = min(list(rank_new.values()) + list(rank_old.values()))
    max_ = max(list(rank_new.values()) + list(rank_old.values()))
    rank_new = {k: scale2range(min_, max_, 0, 100, v) for k, v in rank_new.items()}
    rank_old = {k: scale2range(min_, max_, 0, 100, v) for k, v in rank_old.items()}

    # rank_new = {term: i for i, (term, _score) in enumerate(scaff_latest) if term in shared}
    # rank_old = {term: i for i, (term, _score) in enumerate(scaff_old) if term in shared}
    rank_changes = {term: rank_old[term] - rank_new[term] for term in shared}
    rank_changes = sorted(rank_changes.items(), key=lambda k: k[1], reverse=True)
    print("!")


def check_index():
    t = TweetEx.objects.filter(tweetexindex__term__in=["ai", "AI", "artificial intelligence", "artificial_intelligence"], user__screen_name__iexact="HSGStGallen")
    t = list(t)
    tt = [x.text for x in t]
    print(t)


if __name__ == "__main__":
    # tweets_per_user()
    # date_experiment()
    # print_unigrams()
    # feed_stuff()
    # monthmodel_stuff()
    # calculate_gensim_corpus_feeds()
    # tweet_inheritance_experiment()
    # rename_old_users()
    # User.objects.filter(screen_name="sha_hsg_OLD").delete()
    # User.objects.filter(screen_name="HSGStGallen_OLD").delete()   
    # port_old_users_2_ex()
    # port2new()
    # sitri_exmodel()
    # check_sitri()
    # find_duplicate()
    # spike_experiment()
    check_index()