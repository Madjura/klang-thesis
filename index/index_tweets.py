import json
import os
import pickle
import re
from collections import defaultdict, OrderedDict
from enum import Enum, auto

import readability

from common.text import get_spacy_model
from common.util import default_to_regular
from text.sentence import Sentence
from titaness import setup

setup()
from titaness.settings import DATA_DIR

readability.readability.REGEXES["negativeRe"] = re.compile(
    'combx|comment|com-|contact|foot|footer|footnote|masthead|media|outbrain|promo|related|scroll|shoutbox|sidebar|sponsor|shopping|tags|tool|widget',
    re.I)

from indexapp.models import TweetIndex, TweetExIndex, TextExIndex
from dataapp.models import TweetEx, UserEx, TextEx

TOP_TWEETERS = ["London Business School", "CEIBS", "MIT Sloan School of Management", "Wharton School", "Kellogg School",
                "UCLA Anderson", "Saïd Business School"]


def _tweet_data():
    data_dir = os.path.join(DATA_DIR, "SCAFFIDI")
    with open(os.path.join(data_dir, "scaffidi.p"), "rb") as f:
        scaff = pickle.load(f)
    tops = sorted(scaff.items(), key=lambda k: k[1])
    top_terms = []
    for top, _ in tops:
        if top[0] == "@":
            continue
        top_terms.append(top)
    index = TweetIndex.objects.for_terms(top_terms).select_related("tweet", "tweet__user")
    tweets2date = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
    for i, index_obj in enumerate(index):
        print(f"{i + 1} out of {len(index)}")
        tweet = index_obj.tweet
        month = tweet.created_at.strftime("%m")
        year = tweet.created_at.strftime("%Y")
        tweets2date[tweet.user.name][year][month][index_obj.term] += 1
    tweets2date = default_to_regular(tweets2date)
    json_str = json.dumps(tweets2date)
    data_dir = os.path.join(DATA_DIR, "RANDOM")
    with open(os.path.join(data_dir, "tweets_full.json"), "w") as f:
        f.write(json_str)
    with open(os.path.join(data_dir, "tweets_full.p"), "wb") as f:
        pickle.dump(tweets2date, f)


def load_tweet_data(users=None):
    data_dir = os.path.join(DATA_DIR, "RANDOM")
    try:
        with open(os.path.join(data_dir, "tweets_full.p"), "rb") as f:
            data = pickle.load(f)
    except FileNotFoundError:
        _tweet_data()
        with open(os.path.join(data_dir, "tweets_full.p"), "rb") as f:
            data = pickle.load(f)
    if users:
        data = {user: data[user] for user in users}
    years = set()
    for k, v in data.items():
        years.update(v.keys())
    json_str = json.dumps(data)
    return json_str, {year: 0 for year in years}


def _process_term(term):
    original = term.text.lower()
    return original, original
    if term.like_url:
        term = "#URL#"
    elif term.like_num:
        term = "#NUM#"
    elif term.like_email:
        term = "#EMAIL#"
    elif term.text[0] == "#":
        term = "#HASHTAG#"
    elif term.text[0] == "@":
        term = "#MENTION#"
    elif term.is_stop:
        term = "#STOP#"
    elif term.is_punct:
        term = "#PUNCT#"
    else:
        term = term.text.lower()
    return term, original


def extract_nps_from_sent(sentence):
    nps = []
    terms = []
    np = []
    np_start = -100  # easier to detect bugs if obviously wrong
    np_end = -100
    prev_tag = None
    for pos, (token, tag) in enumerate(sentence):
        token, original = _process_term(token)
        if tag in ["NOUN", "PROPN", "ADJ"]:
            if prev_tag not in ["NOUN", "PROPN", "CCONJ", "ADP"] or not np:
                # start of a new np!
                np_start = pos
                np_end = pos
                np.append(original)
            else:
                # append to NP
                np_end += 1
                np.append(original)
        elif tag in ["CCONJ", "ADP"]:
            # only ok if previous is NOUN or PROPN
            if prev_tag in ["NOUN", "PROPN", "ADJ"]:
                np_end += 1
                np.append(original)  # always add the original, even if stopword etc
                # np.append(token)
        elif np:
            # all other tags
            # this means the NP is over
            if prev_tag in ["CCONJ", "ADP"]:
                # not okay, remove and end NP!
                np = np[:-1]
                np_end -= 1
                nps.append((np_start, np_end, "_".join(np)))
            else:
                # NP is over
                nps.append((np_start, np_end, "_".join(np)))
            # got a tag that cant be part of a NP, so the NP is over. empty it
            np = []
        prev_tag = tag
        terms.append((pos, pos, token))
    return nps, terms


def pos_tag_spacy(text, nlp):
    sentences = []
    text = nlp(text)
    for i, sentence in enumerate(list(text.sents)):
        tokens = OrderedDict()
        for token in sentence:
            tokens[token] = token.pos_
        sentences.append(Sentence(i, tokens))
    return sentences


class IndexType(Enum):
    TWEET = auto()


def _index_external(to_index, index_type: IndexType, lang="en", ):
    """
    Creates TweetExIndex objects for a list of TweetEx objects.

    !!! DOES NOT CHECK FOR ALREADY INDEXED TWEETS. FILTERING MUST BE DONE BEFORE CALLING THE FUNCTION !!!
    Call "index_for_users" instead of calling this directly! Pre-selection / filtering is done there!

    :param to_index: A list of TweetEx objects to be indexed.
    :param lang: Optional. Default: "en". The language of the Tweets. TODO: Do language per Tweet
    """
    nlp = get_spacy_model(lang=lang)
    create = []
    np_check = defaultdict(int)
    for i, elem in enumerate(to_index):
        if i % 100 == 0:
            print(f"--> Indexing Element {i + 1} out of {len(to_index)} ({str(index_type)}) <--")
        if index_type == IndexType.TWEET:
            text = elem.text
        else:
            # please no
            raise Exception("this should never print and if it does then that means that something has gone \
            catastrophically wrong: ERROR CODE: #123pleaseno")
        sents = pos_tag_spacy(text, nlp)
        freqs = defaultdict(int)
        for sent in sents:
            sent_data = [(token, tag) for token, tag in sent.tokens.items()]
            for token, tag in sent_data:
                if tag == "NOUN" or tag == "PROPN":
                    # will also be in "terms" which gives it a -1, +2 to compensate for it
                    np_check[token] += 2
            nps, terms = extract_nps_from_sent(sent_data)
            for _start, _end, np in nps:
                np_check[np] += 1
            for _start, _end, t in terms:
                np_check[t] -= 1
            nps.extend(terms)
            for _start, _end, term in nps:
                freqs[term] += 1
        for term, freq in freqs.items():
            noun = False
            if np_check[term] > 0:
                noun = True
            if index_type == IndexType.TWEET:
                create.append(
                    TweetExIndex(term=term, tweet=elem, count=freq, day=elem.created_at.day,
                                 month=elem.created_at.month, year=elem.created_at.year, noun=noun))
    if index_type == IndexType.TWEET:
        TweetExIndex.objects.bulk_create(create)


def index_for_users(users, lang="en", pr=None):
    to_index_all = []
    for i, user in enumerate(users):
        if pr is not None:
            pr.set_progress(i + 1, len(users), description=f"Indexing Tweets for user {user.screen_name}.")
        to_index = TweetEx.objects.filter(user=user).exclude(
            pk__in=TweetExIndex.objects.filter(tweet__user=user).select_related("tweet").values_list("tweet",
                                                                                                     flat=True))
        to_index_all.extend(to_index)
    _index_external(to_index_all, IndexType.TWEET, lang=lang)


if __name__ == "__main__":
    # f = FeedContent.objects.get(feed__pk=785)
    # _tweet_data()
    # load_tweet_data()
    # tweets_with_top_debug()
    # extract_feeds_content()
    # _tweet_data()
    # TweetExIndex.objects.all().delete()
    _u = UserEx.objects.all()
    index_for_users(_u)
