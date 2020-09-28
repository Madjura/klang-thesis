import datetime
import os
import re

import dill
from django.core.exceptions import ObjectDoesNotExist
from nltk import sent_tokenize, word_tokenize

from common.text import process_term, get_spacy_model
from common.util import default_to_regular
from ontology.ontology import KlangRelationsFix
from titaness import setup

setup()
from titaness.settings import DATA_DIR
from trendapp.models import Tweet
from klangapp.models import ClusterResult


def preprocess(texts, nlp=None):
    texts = [x for x in texts if x]
    if nlp is None:
        nlp = get_spacy_model(lang="en")
    t = []
    for i, doc in enumerate(nlp.pipe(texts, batch_size=50)):
        if i > 0 and i % 100 == 0:
            print(f"--> Preprocessing text {i+1} out of {len(texts)} <--")
        d = []
        for sentence in doc.sents:
            for token in sentence:
                token = process_term(token)
                if token[0] == "#" and token[-1] == "#":
                    continue
                d.append(token)
        t.append(" ".join(d))
    return t


def tokenize_only(text):
    # first tokenize by sentence, then by word to ensure that punctuation is caught as its own token
    tokens = [word.lower() for sent in sent_tokenize(text) for word in word_tokenize(sent)]
    filtered_tokens = []
    # filter out any tokens not containing letters (e.g., numeric tokens, raw punctuation)
    for token in tokens:
        if re.search("[a-zA-Z]", token) and len(token) > 2:
            filtered_tokens.append(token)
    return filtered_tokens


def assign_kws_to_tweets(nouns_only):
    """
    tf-idf approach for all Twitter users.
    Creates Klang output that can be used as input for Klang.
    :param nouns_only:
    :return:
    """
    users = sorted(set(Tweet.objects.filter(text__isnull=False).select_related("user__name")
                       .values_list("user__name", flat=True)))
    # users = ["London Business School"]
    nlp = get_spacy_model(lang="en")
    relations = KlangRelationsFix()
    for i, user in enumerate(users):
        print(f"{i+1} out of {len(users)}")
        tweets = Tweet.objects.filter(text__isnull=False, user__name=user)
        try:
            r = ClusterResult.objects.get(name=user, nouns_only=nouns_only)
        except ObjectDoesNotExist:
            continue
        clusters = r.keywords
        tfidf = r.vectorizer
        tfidf.tokenizer = tokenize_only
        m = r.clusterer

        # data_dir_path = os.path.join(DATA_DIR, "CLUSTER", "tweets", f"{user}")
        # try:
        #     with open(os.path.join(data_dir_path, f"keywords_TWEETS_{user}_{nouns_only}.p"), "rb") as f:
        #         clusters = dill.load(f)
        # except FileNotFoundError:
        #     continue
        # with open(os.path.join(data_dir_path, f"tfidf_{user}_{nouns_only}.p"), "rb") as f:
        #     tfidf = dill.load(f)
        # tfidf.tokenizer = tokenize_only
        # with open(os.path.join(data_dir_path, f"mbatch_{user}_{nouns_only}.p"), "rb") as f:
        #     m = dill.load(f)

        for tweet in tweets:
            text = preprocess([tweet.text], nlp=nlp)
            text = tfidf.transform(text)
            cluster_id = m.predict(text)[0]
            try:
                cluster_elems = clusters[cluster_id].split(",")
            except IndexError:
                continue
            for elem in cluster_elems:
                month = (tweet.created_at.month / 12) - 1/12
                year = tweet.created_at.year
                d = year + month
                relations.add_unquantified("hasKeyword", tweet.pk, elem, d)
                # relations.add_unquantified("userHasKeyword", user, elem, tweet.created_at.year)
    relations.relations = default_to_regular(relations.relations)
    data_dir = os.path.join(DATA_DIR, "KLANG")
    # with open(os.path.join(data_dir, f"titaness_cluster_all_{nouns_only}NEW_FIX.p"), "wb") as f:
    #     dill.dump(relations.relations, f)
    with open(os.path.join(data_dir, f"titaness_cluster_all_{nouns_only}__THESIS.p"), "wb") as f:
        dill.dump(relations.relations, f)


if __name__ == "__main__":
    assign_kws_to_tweets(False)
