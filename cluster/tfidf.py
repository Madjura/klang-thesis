import os
import pickle
import re
from collections import defaultdict

import dill
import math
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
from common.util import default_to_regular
from klang.klangrelations import KlangRelationsFix

from titaness import setup

setup()
from klangapp.models import PreprocessedText, ClusterResult
from titaness.settings import DATA_DIR

from trendapp.models import FeedContent, Feed, Tweet


def tokenize_only(text):
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

    example = ["""
    Are stock buybacks good for business or do companies need to be reined in? Drawing on research by LBS’s 
@aedmans
, the 
@IrishTimes
 looks at the merits of this hot button issue. https://bit.ly/2nnKDHh
    """]
    example = preprocess(example)
    # example = ["The women entrepeneurs are sending applications to the open entrepeneurship cartierawards."]
    example_transform = tfidf.transform(example)
    p = m.predict(example_transform)
    print(p)

    # clusters = KMeans(n_clusters=30, random_state=20).fit_predict(text)
    # plot_tsne_pca(text, clusters)
    get_top_keywords(text, clusters, tfidf.get_feature_names(), 10)


def cluster(texts, identifier=None, plot=True, top=10):
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


def preprocess_feeds():
    feeds = sorted(set(FeedContent.objects.filter(content__isnull=False).select_related("feed")
                       .values_list("feed__channel_title", flat=True)))
    data_dir = os.path.join(DATA_DIR, "CLUSTER", "preprocessed_feeds")
    for i, feed in enumerate(feeds):
        print(f"--> Processing Feeds of channel {feed} ({i + 1} of {len(feeds)}) <--")
        contents = FeedContent.objects.filter(feed__channel_title=feed)
        texts = [x.content for x in contents if x.content]
        if not texts:
            continue
        texts = preprocess(texts)
        with open(os.path.join(data_dir, f"preprocessed_{feed}.p"), "wb") as f:
            pickle.dump(texts, f)


def preprocess_other_texts(texts, identifier):
    data_dir = os.path.join(DATA_DIR, "CLUSTER", f"preprocessed_{identifier}")
    nlp = get_spacy_model(lang="de", for_descriptions=True)
    texts = preprocess(texts, nlp=nlp)
    with open(os.path.join(data_dir, f"preprocessed_{identifier}.p"), "wb") as f:
        pickle.dump(texts, f)


def cluster_other_texts(preprocessed_path):
    relations = KlangRelationsFix()
    nlp = get_spacy_model(lang="de", for_descriptions=True)
    with open(preprocessed_path, "rb") as f:
        texts = pickle.load(f)
    keywords, tfidf, m = cluster(texts, identifier=f"OTHER TEXTS")
    for i, text in enumerate(texts):
        # text = preprocess([text], nlp=nlp)
        text = tfidf.transform([text])
        cluster_id = m.predict(text)[0]
        cluster_elems = keywords[cluster_id]
        for elem in cluster_elems.split(","):
            relations.add_unquantified("hasKeyword", i, elem, 0)
    relations.relations = default_to_regular(relations.relations)
    data_dir = os.path.join(DATA_DIR, "KLANG")
    with open(os.path.join(data_dir, f"titaness_cluster_all_ANGLEGRINDER.p"), "wb") as f:
        dill.dump(relations.relations, f)
    print("!!")


def cluster_tweets_all(users=None, top=3, nouns_only=False, pr=None):
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
        # data_dir_path = os.path.join(DATA_DIR, "CLUSTER", "tweets", f"{user}")
        # if not os.path.exists(data_dir_path):
        #     os.mkdir(data_dir_path)
        # with open(os.path.join(data_dir_path, f"keywords_TWEETS_{user}_{nouns_only}.p"), "wb") as f:
        #     dill.dump(keywords, f)
        # with open(os.path.join(data_dir_path, f"tfidf_{user}_{nouns_only}.p"), "wb") as f:
        #     dill.dump(tfidf, f)
        # with open(os.path.join(data_dir_path, f"mbatch_{user}_{nouns_only}.p"), "wb") as f:
        #     dill.dump(m, f)
    with transaction.atomic():
        for c in objs_update:
            c.save()


def cluster_feeds_all():
    feeds = sorted(set(FeedContent.objects.filter(content__isnull=False).select_related("feed")
                       .values_list("feed__channel_title", flat=True)))
    data_dir = os.path.join(DATA_DIR, "CLUSTER", "preprocessed_feeds")
    for i, feed in enumerate(feeds):
        print(f"--> Clustering for {feed} ({i + 1} of {len(feeds)}) <--")
        try:
            with open(os.path.join(data_dir, f"preprocessed_{feed}.p"), "rb") as f:
                texts = pickle.load(f)
        except FileNotFoundError:
            continue
        keywords = cluster(texts, identifier=f"Feeds for {feed}")
        if not keywords:
            continue
        with open(os.path.join(DATA_DIR, "CLUSTER", "feeds", f"keywords_{feed}.p"), "wb") as f:
            pickle.dump(keywords, f)


def keyword_experiment(path=".", name_only=None):
    files = os.listdir(path)
    d = {}
    for file in files:
        if file[:8] == "keywords":
            name = file[9:-2]
            if name_only and name != name_only:
                continue
            with open(os.path.join(path, file), "rb") as f:
                data = pickle.load(f)
            data = [x.split(",") for x in data]
            d[name] = data
    kw_scores = defaultdict(lambda: list())
    total_clusters = 0
    for k, clusters in d.items():
        total_clusters += len(clusters)
        for kw_list in clusters:
            for i, kw in enumerate(kw_list):
                pos = 1 - i
                kw_scores[kw].append(pos)
    kw_scores2 = {kw: (sum(scores)) * math.log(total_clusters / len(scores)) for kw, scores in kw_scores.items() if
                  len(scores) > 1}
    kw_scores2 = sorted(kw_scores2.items(), key=lambda k: k[1], reverse=True)
    interesting = ["machine learning", "ai", "artificial intelligence", "deep learning", "mba", "emba"]
    foo = []
    for t in interesting:
        foo.extend([x for x in kw_scores2 if x[0] == t])
    print(kw_scores2)
    possible = {k: v for k, v in d.items() for x in v if "artificial intelligence" in x}
    d = {}
    for k, v in possible.items():
        d[k] = set([x for y in v for x in y])
    for k, v in d.items():
        for kk, vv in d.items():
            if kk == k:
                continue
            foo = v.intersection(vv)
            print(foo)
    print(d)


def assign_kws_to_tweets():
    """
    TODO: debug only? probably? maybe?
    :return:
    """
    users = sorted(set(Tweet.objects.filter(text__isnull=False).select_related("user__name")
                       .values_list("user__name", flat=True)))
    users = ["London Business School"]
    for user in users:
        tweets = Tweet.objects.filter(text__isnull=False, user__name=user)
        data_dir_path = os.path.join(DATA_DIR, "CLUSTER", "tweets", f"{user}")
        with open(os.path.join(data_dir_path, f"keywords_TWEETS_{user}"), "rb") as f:
            clusters = dill.load(f)
        with open(os.path.join(data_dir_path, f"tfidf_{user}.p"), "rb") as f:
            tfidf = dill.load(f)
        with open(os.path.join(data_dir_path, f"mbatch_{user}.p"), "rb") as f:
            m = dill.load(f)
        for tweet in tweets:
            text = preprocess(tweet.text)
            text = tfidf.transform(text)
            cluster_id = m.predict(text)[0]
            # cluster_elems = clusters[cluster]
            # new, should be correct? old is above, commented o
            cluster_elems = clusters[cluster_id]
            print(cluster_elems)


if __name__ == "__main__":
    # feed_count()
    # __cluster_feeds()
    __cluster_tweets()

    # preprocess_tweets(nouns_only=False)
    # cluster_tweets_all(top=5, nouns_only=False)

    # keyword_experiment(name_only="London Business School")
    # preprocess_feeds()
    # cluster_feeds_all()
    # assign_kws_to_tweets()

    # product_experiment()
