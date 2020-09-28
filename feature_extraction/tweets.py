import pickle
from collections import defaultdict

from django.db import transaction
from spacymoji import Emoji

from common.text import get_spacy_model
from titaness import setup

setup()
from indexapp.models import TweetIndex
from trendapp.models import Tweet


def index_tweets(tweets, lemmatize=True, min_len=3):
    existing = TweetIndex.objects.filter(tweet__in=tweets).values_list("tweet", flat=True)
    required = set(x.pk for x in tweets).difference(set(existing))
    nlp = get_spacy_model(lang="en")
    emoji = Emoji(nlp, merge_spans=False)
    nlp.add_pipe(emoji, first=True)
    unigram_counts = defaultdict(int)
    bigram_counts = defaultdict(int)
    texts = [x.text for x in tweets]
    index_unigram = []
    index_bigram = []
    prev = None
    prev_lemma = None
    existing = defaultdict(lambda: False)
    for i, doc in enumerate(nlp.pipe(texts, batch_size=100)):
        tweet = tweets[i]
        print(f">>> Processing tweet {i+1} out of {len(tweets)} <<<")
        for sentence in doc.sents:
            bigram_noun_candidate = None
            for token in sentence:
                if token._.is_emoji:
                    # TODO: check if necessary
                    bigram_noun_candidate = None
                    continue
                if tweets[i].pk in required:
                    # TODO: check if indexing emojis is necessary
                    if not existing[(tweet.pk, token.text)]:
                        index_unigram.append(TweetIndex(term=token.text, tweet=tweet, bigram=False, lemmatized=False))
                        existing[(tweet.pk, token.text)] = True
                    if not existing[(tweet.pk, token.lemma_)]:
                        index_unigram.append(TweetIndex(term=token.lemma_, tweet=tweet, bigram=False, lemmatized=True))
                        existing[(tweet.pk, token.lemma_)] = True
                    if token.is_digit and not existing[(tweet.pk, "#NUM#")]:
                        index_unigram.append(TweetIndex(term="#NUM#", tweet=tweet, bigram=False, lemmatized=True))
                    if prev and prev_lemma:
                        if not existing[(tweet.pk, f"{prev}<BIGRAM>{token.text}")]:
                            index_bigram.append(TweetIndex(term=f"{prev}<BIGRAM>{token.text}", tweet=tweet,
                                                           bigram=True, lemmatized=False))
                            existing[(tweet.pk, f"{prev}<BIGRAM>{token.text}")] = True
                        if not existing[(tweet.pk, f"{prev_lemma}<BIGRAM>{token.lemma_}")]:
                            index_bigram.append(TweetIndex(term=f"{prev_lemma}<BIGRAM>{token.lemma_}", tweet=tweet,
                                                           bigram=True, lemmatized=True))
                            existing[(tweet.pk, f"{prev_lemma}<BIGRAM>{token.lemma_}")] = True
                prev = token.text
                prev_lemma = token.lemma_
                if token.pos_ in ["NOUN", "PRPN"]:
                    if lemmatize:
                        text = token.lemma_
                    else:
                        text = token.text
                    if len(text) < min_len:
                        bigram_noun_candidate = None
                        continue
                    unigram_counts[text] += 1
                    if bigram_noun_candidate:
                        first, second = bigram_noun_candidate, text
                        bigram_counts[f"{first}<BIGRAM>{second}"] += 1
                    bigram_noun_candidate = text
                else:
                    bigram_noun_candidate = None
    unigram_counts = dict(unigram_counts)
    bigram_counts = dict(bigram_counts)
    with open("unigram_counts.p", "wb") as f:
        pickle.dump(unigram_counts, f)
    with open("bigram_counts.p", "wb") as f:
        pickle.dump(bigram_counts, f)
    with transaction.atomic():
        TweetIndex.objects.bulk_create(index_unigram)
    with transaction.atomic():
        TweetIndex.objects.bulk_create(index_bigram)


def index_numbers():
    index = list(TweetIndex.objects.filter(bigram=False).select_related("tweet"))
    create = []
    existing = defaultdict(lambda: False)
    for i, entry in enumerate(index):
        print(f">> Number index fix method: {i+1} out of {len(index)} <<")
        term = entry.term
        try:
            float(term)
            if not existing[entry.tweet]:
                create.append(TweetIndex(term="#NUM#", tweet=entry.tweet, bigram=False, lemmatized=True))
                existing[entry.tweet] = True
        except ValueError:
            continue
    print(len(create))
    with transaction.atomic():
        TweetIndex.objects.bulk_create(create)


if __name__ == "__main__":
    # _tweets = Tweet.objects.for_more_than(500)
    # _texts = [x.text for x in _tweets]
    # index_tweets(_tweets)
    index_numbers()
