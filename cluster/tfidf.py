from titaness import setup

setup()

import re

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from nltk import word_tokenize, sent_tokenize
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE

from common.text import get_spacy_model, process_term

from klangapp.models import PreprocessedText, ClusterResult

from trendapp.models import Tweet


def tokenize_only(text):
    """
    Tokenizer used for the TfIdfVectorizer.
    Filters out any empty tokens.
    :param text: The text.
    :return: The filtered text.
    """
    # based on nltk.sent_tokenize, but simpler
    # first tokenize by sentence, then by word to ensure that punctuation is caught as its own token
    tokens = [word.lower() for sent in sent_tokenize(text) for word in word_tokenize(sent)]
    filtered_tokens = []
    # filter out any tokens not containing letters (e.g., numeric tokens, raw punctuation)
    for token in tokens:
        if re.search("[a-zA-Z]", token) and len(token) > 2:
            filtered_tokens.append(token)
    return filtered_tokens


def preprocess(texts, nouns_only=False, nlp=None):
    """
    Preprocesses texts used in the tf-idf approach.
    Removes hashtags, URLs, numbers, ...
    :param texts: A list of texts.
    :param nlp: The spaCy object used to split the texts into tokens.
    :return: The texts, but preprocessed.
    """
    texts = [x for x in texts if x]
    if nlp is None:
        nlp = get_spacy_model(lang="en")
    t = []
    for i, doc in enumerate(nlp.pipe(texts, batch_size=50)):
        if i % 100 == 0:
            print(f"--> Preprocessing text {i + 1} out of {len(texts)} <--")
        d = []
        for sentence in doc.sents:
            for token in sentence:
                token = process_term(token, nouns_only=nouns_only)
                if token[0] == "#" and token[-1] == "#":
                    continue
                d.append(token)
        t.append(" ".join(d))
    return t


def find_optimal_clusters(data, max_k, plot=True, identifier=None):
    """
    Finds the number of clusters between 1 and max_k so that the inertia is minimized.
    Additionally plots the inertia values, as shown in the thesis.
    :param data: Output of TfidfVectorizer, vectorized documents.
    :param max_k: The maximum number of clusters to check for.
    :param plot: Optional. Default: True. Whether or not the inertia values should be plotted or not.
    :param identifier: Optional. Default: None. The label to use in the plot.
    :return: The minimum inertia value and the number of clusters to achieve this.
    """
    iters = range(1, max_k + 1, 1)
    sse = []
    min_val = 100000
    min_index = -1
    for k in iters:
        val = MiniBatchKMeans(n_clusters=k, init_size=1024, batch_size=2048, random_state=20).fit(data).inertia_
        sse.append(val)
        if val < min_val:
            min_val = val
            min_index = k
        print('Fit {} clusters'.format(k))
    if plot:
        f, ax = plt.subplots(figsize=(20, 10))
        ax.plot(iters, sse, marker='o')
        ax.set_xlabel('Cluster Centers')
        ax.set_xticks(iters)
        ax.set_xticklabels(iters)
        ax.set_ylabel('SSE')
        if identifier:
            ax.set_title(identifier)
        else:
            ax.set_title('SSE by Cluster Center Plot')
        plt.show()
    return min_val, min_index


def get_top_keywords(data, clusters, labels, n_terms):
    """
    Gets the top keywords from topic clusters.
    Based on the highest average tf-idf value.
    :param data: The output of the TfidfVectorizer, the vectorized documents.
    :param clusters: The clusters that each text belongs to.
    :param labels: The labels of the TfidfVectorizer features, in other words the terms.
    :param n_terms: How many terms to use for each topic cluster.
    :return: The terms to assign.
    """
    df = pd.DataFrame(data.todense()).groupby(clusters).mean()
    out = []
    for i, r in df.iterrows():
        print(f"\nCluster {i + 1}")
        terms = ",".join(labels[t] for t in np.argsort(r)[-n_terms:])
        print(terms)
        out.append(terms)
    return out


def plot_tsne_pca(data, labels):
    max_label = max(labels)
    max_items = np.random.choice(range(data.shape[0]), size=3000, replace=False)

    pca = PCA(n_components=2).fit_transform(data[max_items, :].todense())
    tsne = TSNE().fit_transform(PCA(n_components=50).fit_transform(data[max_items, :].todense()))

    idx = np.random.choice(range(pca.shape[0]), size=3000, replace=False)
    label_subset = labels[max_items]
    label_subset = [cm.hsv(i / max_label) for i in label_subset[idx]]

    f, ax = plt.subplots(1, 1, figsize=(20, 10))

    ax[0].scatter(pca[idx, 0], pca[idx, 1], c=label_subset)
    ax[0].set_title('PCA Cluster Plot')

    ax[1].scatter(tsne[idx, 0], tsne[idx, 1], c=label_subset)
    ax[1].set_title('TSNE Cluster Plot')
    plt.show()


def __cluster_tweets():
    """
    TODO: debug only probably?
    :return:
    """
    tweets = Tweet.objects.filter(user__screen_name="LBS")
    # tweets = Tweet.objects.filter(text__isnull=False)
    # tweets = Tweet.objects.filter(user__name="Kellogg School")
    # tweets = Tweet.objects.filter(user__name="INSEAD")
    text = [x.text for x in tweets]
    text = preprocess(text)
    tfidf = TfidfVectorizer(max_df=0.8, max_features=1000,
                            min_df=0, stop_words='english',
                            use_idf=True, tokenizer=tokenize_only, ngram_range=(1, 4))
    text = tfidf.fit_transform(text)
    # ideal_val, ideal_clusters = find_optimal_clusters(text, 100)
    ideal_val, ideal_clusters = find_optimal_clusters(text, tweets.count())
    print(f"--> Ideal clusters: {ideal_clusters} ---- Ideal val: {ideal_val} <---")
    m = MiniBatchKMeans(n_clusters=ideal_clusters, init_size=1024, batch_size=2048, random_state=20)
    clusters = m.fit_predict(text)
    # clusters = KMeans(n_clusters=30, random_state=20).fit_predict(text)
    # plot_tsne_pca(text, clusters)
    get_top_keywords(text, clusters, tfidf.get_feature_names(), 10)


def cluster(texts, identifier=None, plot=True, top=10):
    """
    Clusters texts and assigns keywords as per tf-idf approach.
    :param texts: The texts.
    :param identifier: The name to give the clustering result, for example the Twitter name.
    :param plot: Optional. Default: True. Whether or not to plot the inertia values.
    :param top: Optional. Default: 10. How many terms to pull from each topic clusters.
    :return: The keywords, the vectorizer and the result of the MinibatchKmeans.
    """
    n_texts = len(texts)
    tfidf = TfidfVectorizer(max_df=0.8, max_features=1000,
                            min_df=0, stop_words='english',
                            use_idf=True, tokenizer=tokenize_only, ngram_range=(1, 4))
    try:
        # empty vocabulary, happens for users with only 1 tweet, safe to filter out
        if len(texts) == 1:
            texts.append("")
        texts = tfidf.fit_transform(texts)
    except ValueError:
        return None, None, None
    n_clusters = 100 if n_texts >= 100 else n_texts
    ideal_val, ideal_clusters = find_optimal_clusters(texts, n_clusters, identifier=identifier, plot=plot)
    m = MiniBatchKMeans(n_clusters=ideal_clusters, init_size=1024, batch_size=2048, random_state=20)
    clusters = m.fit_predict(texts)
    return get_top_keywords(texts, clusters, tfidf.get_feature_names(), top), tfidf, m


def preprocess_tweets(nouns_only=False, pr=None):
    """
    Preprocesses Tweets for use in the tf-idf approach.
    :param nouns_only: Optional. Default: False. Whether only nouns should be used.
    :param pr: Optional. Can be used to record progress for large datasets.
    :return:
    """
    users = set(Tweet.objects.filter(text__isnull=False).select_related("user__name")
                .values_list("user__name", flat=True))
    # data_dir = os.path.join(DATA_DIR, "CLUSTER", "preprocessed_tweets")
    objs_update = []
    nlp = get_spacy_model(lang="en")
    for i, user in enumerate(users):
        if pr is not None:
            pr.set_progress(i + 1, len(users), description=f"Processing Tweets of user {user}.")
        else:
            print(f"--> Processing Tweets of user {user} ({i + 1} of {len(users)}) <--")
        tweets = Tweet.objects.filter(text__isnull=False, user__name=user)
        texts = [x.text for x in tweets if x.text]
        if not texts:
            continue
        texts = preprocess(texts, nouns_only=nouns_only, nlp=nlp)
        m, _created = PreprocessedText.objects.get_or_create(name=user, nouns_only=nouns_only)
        m.texts = texts
        objs_update.append(m)
    with transaction.atomic():
        for obj in objs_update:
            obj.save()


def cluster_tweets_all(users=None, top=3, nouns_only=False, pr=None):
    """
    Produces tf-idf approach results for a list of users.
    Uses the database, data must be loaded first or crawled and stored in db.
    :param users: The users.
    :param top: How many terms to use for each clusters.
    :param nouns_only: Whether only nouns should be used.
    :param pr: Can be used to record progress for long running tasks.
    :return:
    """
    if users is None:
        users = sorted(set(Tweet.objects.filter(text__isnull=False).select_related("user__name")
                           .values_list("user__name", flat=True)))
    objs_update = []
    for i, user in enumerate(users):
        if pr is not None:
            pr.set_progress(i + 1, len(users), description=f"Clustering Tweets for user {user}.")
        print(f"--> Clustering for {user} ({i + 1} of {len(users)}) <--")

        try:
            # TODO: potential conflict? maybe needs transactions or something
            texts = PreprocessedText.objects.get(name=user, nouns_only=nouns_only).texts
            print(len(texts))
        except ObjectDoesNotExist:
            continue
        keywords, tfidf, m = cluster(texts, identifier=f"Tweets for {user}", plot=False, top=top)
        if not keywords:
            continue
        c, _created = ClusterResult.objects.get_or_create(name=user, nouns_only=nouns_only)
        c.keywords = keywords
        c.vectorizer = tfidf
        c.clusterer = m
        objs_update.append(c)
    with transaction.atomic():
        for c in objs_update:
            c.save()


if __name__ == "__main__":
    _users = ["lbs", "KellogSchool"]
    # __cluster_tweets()

    # preprocess first
    # preprocess_tweets()

    # then process and get results
    cluster_tweets_all(_users)
