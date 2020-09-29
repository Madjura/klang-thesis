from django.core.exceptions import ObjectDoesNotExist

from cluster.tfidf import cluster
from common.util import default_to_regular
from klang.klangrelations import KlangRelationsFix
from titaness import setup

setup()

from common.text import get_spacy_model, process_term
from klangapp.models import PreprocessedText, ClusterResult, KlangInput
from dataapp.models import TweetEx


def preprocess_tweets_ex(user, lang="en", nlp=None):
    """
    Preprocess external Tweets.
    :param user: The screen name of the user.
    :param lang: Optional. Default: "en". The language of the Tweets.
    :param nlp: Optional. Default: None. The spaCy model to use.
    :return: A PreprocessedText representing the texts of the user.
    """
    tweets = TweetEx.objects.filter(user__screen_name=user)
    start = min(x.created_at for x in tweets)
    end = max(x.created_at for x in tweets)
    if nlp is None:
        nlp = get_spacy_model(lang=lang)
    texts = [x.text for x in tweets if x.text]
    texts = preprocess(texts, nlp=nlp)
    m, _created = PreprocessedText.objects.get_or_create(name=user, nouns_only=True, external=True, start=start,
                                                         end=end)
    m.texts = texts
    m.save()
    return m


def preprocess(texts, nlp=None):
    texts = [x for x in texts if x]
    if nlp is None:
        nlp = get_spacy_model(lang="en")
    t = []
    for i, doc in enumerate(nlp.pipe(texts, batch_size=50)):
        if i > 0 and i % 100 == 0:
            print(f"--> Preprocessing text {i + 1} out of {len(texts)} <--")
        d = []
        for sentence in doc.sents:
            for token in sentence:
                token = process_term(token, nouns_only=True)
                if token[0] == "#" and token[-1] == "#":
                    continue
                d.append(token)
        t.append(" ".join(d))
    return t


def cluster_tweets_external(texts: PreprocessedText, top=3):
    """
    Clusters Tweets, from preprocessed texts in db.
    :param texts: PreprocessedText objects representing the texts.
    :param top: The number of keywords to assign to each clusters.
    :return: The ClusterResult representing the result.
    """
    keywords, tfidf, m = cluster(texts.texts, identifier=f"Tweets for {texts.name}", plot=False, top=top)
    c, _created = ClusterResult.objects.get_or_create(name=texts.name, nouns_only=True, external=True, texts=texts)
    c.keywords = keywords
    c.vectorizer = tfidf
    c.clusterer = m
    c.save()
    return c


def assign_kws_to_tweets_external(clusters: [ClusterResult], name: str, lang="en", pr=None):
    """
    Assigns KWs to Tweets, uses the database.
    :param clusters: ClusterResult objects representing the topic clusters.
    :param name: The name of the output.
    :param lang: The language of the texts.
    :param pr: Can be used to record progress for long running tasks.
    :return: Nothing, results are stored in database as KlangInput instances.
    """
    nlp = get_spacy_model(lang=lang)
    relations = KlangRelationsFix()
    for i, cluster_obj in enumerate(clusters):
        if pr is not None:
            pr.set_progress(i + 1, len(clusters), description=f"Assigning keywords to Tweets.")
        texts = cluster_obj.texts
        kws = cluster_obj.keywords
        tweets = texts.get_tweets()
        tfidf = cluster_obj.vectorizer
        m = cluster_obj.clusterer
        for tweet in tweets:
            text = preprocess([tweet.text], nlp=nlp)
            text = tfidf.transform(text)
            cluster_id = m.predict(text)[0]
            try:
                cluster_elems = kws[cluster_id].split(",")
            except IndexError:
                continue
            for elem in cluster_elems:
                month = (tweet.created_at.month / 12) - 1 / 12
                year = tweet.created_at.year
                d = year + month
                relations.add_unquantified("hasKeyword", tweet.pk, elem, d)
    relations.relations = default_to_regular(relations.relations)
    # TODO: clear out old clusters m2m?
    try:
        m = KlangInput.objects.get(name=name)
    except ObjectDoesNotExist:
        m = KlangInput(name=name)
    m.model = relations
    m.save()
    m.clusters.clear()
    m.clusters.add(*clusters)


if __name__ == "__main__":
    # preprocess tweets
    _t = preprocess_tweets_ex("sha_hsg")
    # then cluster
    _c = cluster_tweets_external(_t)
    # then assign keywords
    assign_kws_to_tweets_external([_c], "Experiment")