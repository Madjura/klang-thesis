import math
import operator
import sys
from collections import defaultdict
from functools import reduce

from django.db import OperationalError
from django.db.models import Q, Sum

from titaness import setup

setup()
from wikipediaapp.models import Words, CoN
from dataapp.models import UserEx
from indexapp.models import TweetIndex, TweetExIndex
from django.core.exceptions import ObjectDoesNotExist


def _total_count(use_index=False, users=None):
    if use_index and users is not None:
        # TODO: check which is correct
        # other_users = UserEx.objects.exclude(pk__in=users.values_list("pk", flat=True))
        other_users = users  # might be wrong
        count = TweetExIndex.objects.filter(tweet__user__in=other_users).aggregate(Sum("count"))["count__sum"]
        return count
    else:
        return Words.objects.all().count()


def _freqs(words):
    return defaultdict(int, {w.word: w.freq for w in Words.objects.filter(word__in=words)})


def _bigram_counts(bigrams):
    print(len(bigrams))
    # iconcat is +=
    flat = list(set(reduce(operator.iconcat, bigrams, [])))
    # get w_ids of all the terms occuring in bigrams
    wq = Words.objects.filter(word__in=flat)
    w_ids = defaultdict(int, {w.word: w.w_id for w in wq})
    w_reverse = {w.w_id: w.word for w in Words.objects.filter(word__in=flat)}
    # w_ids_fix = defaultdict(lambda: False, {(w.word, w.w_id): True for w in Words.objects.filter(word__in=flat)})
    # keep only those pairs that actually have frequencies
    # bigrams = [[w1, w2] for w1, w2 in bigrams if w1 in w_ids and w2 in w_ids]
    # get ids of bigrams
    bigram_ids = [(w_ids[w1], w_ids[w2]) for w1, w2 in bigrams]
    id1, id2 = bigram_ids[0]
    bigram_ids = bigram_ids[1:]
    q = Q(w1_id=id1, w2_id=id2)
    print("--> Generating big Q query <--")
    for i, (id1, id2) in enumerate(bigram_ids):
        print(f"{i + 1} out of {len(bigram_ids)}")
        q |= Q(w1_id=id1, w2_id=id2)
    print(">!! Executing big Q query <!!")
    q = list(CoN.objects.filter(q))
    print("--> Big Q query finished! <--")
    print(len(q))
    freqs = defaultdict(int)
    for con in q:
        freqs[(con.w1_id, con.w2_id)] = con.freq

    # get all ids of first term of bigrams and all ids of second one
    # w1_ids, w2_ids = zip(*bigram_ids)
    # filter all CoN objects that have the proper w1s and w2s. havent found a faster / better way to do it than this
    # TODO: check if theres a better way
    # cons = CoN.objects.filter(w1_id__in=w1_ids, w2_id__in=w2_ids)
    # get bigram frequencies
    # freqs = defaultdict(int)
    # for i, (w1_id, w2_id) in enumerate(bigram_ids):
    #     print(f"--> Processing bigram {i+1} out of {len(bigrams)} <--")
    #     for con in cons:
    #         if w1_id == con.w1_id and w2_id == con.w2_id:
    #             freqs[(w1_id, w2_id)] = con.freq

    freqs_fix = {}
    for k, v in freqs.items():
        w1, w2 = k
        w1 = w_reverse[w1]
        w2 = w_reverse[w2]
        freqs_fix[(w1, w2)] = v
    # for i, (w1, w2) in enumerate(bigrams):
    #     print(f"--> Processing bigram {i+1} out of {len(bigrams)} <--")
    #     for con in cons:
    #         # if w_ids_fix[(w1, con.w1_id)]:
    #         #     freqs[(w1, w2)] = con.freq
    #         if con.w1_id == w_ids[w1] and con.w2_id == w_ids[w2]:
    #             freqs[(w1, w2)] = con.freq

    import pprint
    pprint.pprint(freqs_fix)
    return freqs_fix


def _reference_freq(term, use_index, users):
    if use_index and users is not None:
        other_users = UserEx.objects.exclude(pk__in=users.values_list("pk", flat=True))
        count = TweetExIndex.objects.filter(term=term, tweet__user__in=other_users).aggregate(Sum("count"))[
            "count__sum"]
        return count
    else:  #
        try:
            w = Words.objects.get(word=term)
            return w.freq
        except ObjectDoesNotExist:
            return None
        except OperationalError:
            # goddamn emojis
            return None


def _scaff_unigram(freqs, word_freqs, total_count, unigram_px_average):
    scaff = {}
    for j, (feature, freq) in enumerate(freqs.items()):
        print(f">-> Processing unigram freq {j + 1} out of {len(freqs.items())} <-<")
        if not feature:
            continue
        nx = freq
        try:
            px = word_freqs[feature] / total_count
        except ZeroDivisionError:
            px = 0  # happens in spike when there is only one feature
        if not px:
            # if this is commented out then words that do NOT appear in the reference corpus are discared
            px = unigram_px_average
            # continue
        try:
            score = (nx - px * total_count) - (nx * math.log((nx / px * total_count))) - (math.log(nx) / 2)
        except ValueError:
            score = 0  # happens in spike when there is only one feature, because of course it does
        scaff[feature] = score
    return scaff


def scaffidi_spike(freqs, freqs_reference):
    """
    Scaffidi score calculation for the sp⬆️ke algorithm.
    :param freqs:
    :param freqs_reference:
    :return:
    """
    total_count = sum(freqs_reference.values())
    word_freqs = defaultdict(int)
    for i, word in enumerate(freqs.keys()):
        freq = freqs_reference.get(word, 0)
        word_freqs[word] += freq
    try:
        unigram_px_average = sum(freqs.values()) / len(freqs)
    except ZeroDivisionError:
        unigram_px_average = 0  # happens in spike, when there is only one aspect
    scaff = _scaff_unigram(freqs, word_freqs, total_count, unigram_px_average)
    return scaff


def scaffidi(unigram_freqs, bigram_freqs, skip_bigrams=True, users_as_reference=False, users=None):
    """
    Calculates Scaffidi score for unigrams and bigrams.

    :param: unigram_freqs: The unigrams with frequency.
    :param: bigram_freqs: The bigrams with frequency.
    :param: skip_bigrams: Optional. Default: False. Whether or not to skip bigrams. Skipping them causes a large
        speedup.
    :param: users_as_reference: Optional. Default: False. When set to True "users" must be passed. When set to "False"
        uses the Wikipedia dump as a reference corpus, otherwise it uses the texts of the users specified in the
        argument as the reference corpus.
    :return:
    """
    # total_count = get_total_words_count_wikipedia()
    total_count = _total_count(users_as_reference, users)
    bigrams_list = []
    for bigrams, _ in bigram_freqs.items():
        bigrams_list.append(bigrams.split("<BIGRAM>"))
    # word_freqs = get_wordcounts_german([x for x, _ in unigram_freqs.items()])
    # word_freqs = _freqs([x for x, _ in unigram_freqs.items()])
    word_freqs = {}
    for i, word in enumerate(unigram_freqs.keys()):
        print(f">-> Getting frequency for word {i + 1} out of {len(unigram_freqs.keys())} <-<")
        freq = _reference_freq(word, users_as_reference, users)
        if freq is None:
            continue
        word_freqs[word] = freq
    # bi_freqs = get_wordcounts_german_bigrams(bigrams_list)

    # handle unigram frequencies, calculate score and save
    unigram_px_average = sum(unigram_freqs.values()) / len(unigram_freqs)
    word_freqs = defaultdict(int, word_freqs)
    scaff = _scaff_unigram(unigram_freqs, word_freqs, total_count, unigram_px_average)
    # bigram frequencies
    i = 0
    if not skip_bigrams:
        bi_freqs = _bigram_counts(bigrams_list)
        scaff_bigrams = {}
        bigram_px_average = sum(bigram_freqs.values()) / len(bigram_freqs)
        for j, (bigram_feature, freq) in enumerate(bigram_freqs.items()):
            print(f">-> Processing bigram freq {j + 1} out of {len(bigram_freqs.items())} <-<")
            i += 1
            w1, w2 = bigram_feature.split("<BIGRAM>")
            if not (w1 or w2):
                continue
            nx = freq
            bi_freq = bi_freqs[(w1, w2)]
            if not bi_freq:
                bi_freq = bi_freqs[(w2, w1)]
            px = bi_freq / total_count
            if not px:
                px = bigram_px_average
            score = (nx - px * total_count) - (nx * math.log((nx / px * total_count))) - (math.log(nx) / 2)
            scaff_bigrams[(w1, w2)] = score
    return scaff


def filter_unigrams_bigrams(unigram_freqs, bigram_freqs, skip_bigrams=False):
    """
    Filters the unigrams and bigrams by the sqrt of the average frequency.

    :param unigram_freqs: A dictionary mapping the unigrams to their frequency.
    :param bigram_freqs: A dictionary mapping the bigrams to their frequency.
    :param skip_bigrams: Optional. Default: False. Whether or not bigrams should be excluded. Skipping them will result
        in a huge speed increase.
    :return: The filtered unigram and bigram freqs.
    """
    unigram_minimum = round(math.sqrt(sum(unigram_freqs.values()) / len(unigram_freqs)))
    if not skip_bigrams:
        bigram_minimum = round(math.sqrt(sum(bigram_freqs.values()) / len(bigram_freqs)))
        print(f"Bigram length before filter: {len(bigram_freqs)}")
        bigram_freqs = {key: value for key, value in bigram_freqs.items() if value >= bigram_minimum}
        print(f"Bigram length after filter: {len(bigram_freqs)}")
    print(f"Unigram length before filter: {len(unigram_freqs)}")
    unigram_freqs = {key: value for key, value in unigram_freqs.items() if value >= unigram_minimum}
    print(f"Unigram length after filter: {len(unigram_freqs)}")
    return unigram_freqs, bigram_freqs


def get_freqs():
    unigram_freqs = defaultdict(int)
    bigram_freqs = defaultdict(int)
    index = TweetIndex.objects.all()
    for entry in index:
        if entry.bigram:
            bigram_freqs[entry.term] += 1
        else:
            unigram_freqs[entry.term] += 1
    return unigram_freqs, bigram_freqs


def _get_index_freq(index, min_length):
    unigram_freqs = defaultdict(int)
    for entry in index:
        term = entry.term
        # calculate the length of the term if we exclude the non-alphabetic characters
        l = len(term) - sum(1 for c in term if not c.isalpha())
        # give a huge penalty to mentions, hashtags and retweets
        if term[0] in ["@", "#"] or term[:3] == "rt_":
            l -= sys.maxsize
        # ignore all terms that are too short
        if l < min_length:
            continue
        unigram_freqs[term] += entry.count
    return unigram_freqs


def get_freqs_spike(tweets, min_length=3, nouns_only=True):
    index = TweetExIndex.objects.filter(tweet__in=tweets, noun=nouns_only)
    unigram_freqs = _get_index_freq(index, min_length)
    return unigram_freqs


def get_freqs_ex(users=None, min_length=3, nouns_only=True):
    """
    # TODO: remove bigrams properly from other functions
    Returns a mapping of terms to their frequency.
    A queryset of UserEx objects can be passed, in which case only the frequencies of those users will be returned.
    The frequencies and terms are based on the TweetExIndex instances.
    Filters out mentions (start with "@") hashtags (start with "#") and retweeets (start with "rt_").
    Filters out all terms that are below a minimum length, which by default is set to 3. Only alphabetic characters
    count towards this minimum length.

    !!! The texts need to be indexed before this function works properly !!!

    :param: users: Optional. Must be a queryset of UserEx objects. If passed only the texts of the specified users
        will be considered.
    :param: min_length: Optional. Default: 3. The minimum length that terms must have to be considered.
    :param: nouns_only: Optional. Default: True. Whether or not to consider only nouns.
    :return: A dictionary mapping terms to their frequency for unigrams, and an empty dictionary for bigrams.
    """
    bigram_freqs = defaultdict(int)
    # get all relevant index entries
    if not users:
        index = TweetExIndex.objects.filter(noun=nouns_only)
    else:
        index = TweetExIndex.objects.filter(tweet__user__in=users, noun=nouns_only)
    unigram_freqs = _get_index_freq(index, min_length)
    return unigram_freqs, bigram_freqs


def feature_extraction_full_ex(users, users_as_reference=False, other_users=None, min_length=0, nouns_only=True):
    """
    Performs "feature" extraction on external data.
    The "features" are terms that a certain user uses in their texts that appear more often there than in a reference
    corpus, generally speaking.

    :param: users: A UserEx queryset. The users for which the "features" are to be extracted.
    :param: users_as_reference: Optional. Default: False. Whether or not the texts of other users are to be used as the
        reference corpus. If set to True, the "other_users" argument is required.
        If set to False a version of the English Wikipedia will be used as the reference corpus.
    :param: other_users: Required if "users_as_reference" is set to True. The users for whom the associated texts will
        be used as the reference corpus.
    :param: min_length: Optional. Default: 3. The minimum length that a term needs to have to be considered for the
        feature extraction.
    :param: nouns_only: Optional. Default: True. Whether or not only nouns are to be used for the feature extraction.
    :return: A sorted list in the format [ (score1, feature1), (score2, feature2), ... ], where a lower score indicates
        that the feature is more likely to actually be a feature / is more relevant.
    """
    # feex calls this with a single user
    unigrams, bigrams = get_freqs_ex(users, min_length=min_length, nouns_only=nouns_only)
    unigrams, bigrams = filter_unigrams_bigrams(unigrams, bigrams, skip_bigrams=True)
    scaff = scaffidi(unigrams, bigrams, skip_bigrams=True, users_as_reference=users_as_reference, users=other_users)
    scaff = sorted(scaff.items(), key=lambda k: k[1])
    return scaff


def feature_extraction_spike(tweets, reference_tweets, min_length=3, nouns_only=True):
    """
    Feature extraction for the sp⬆️ke algorithm.
    :param tweets:
    :param reference_tweets:
    :param min_length:
    :param nouns_only:
    :return:
    """
    unigrams = get_freqs_spike(tweets, min_length, nouns_only)
    unigrams_reference = get_freqs_spike(reference_tweets, min_length, nouns_only)
    scaff = scaffidi_spike(unigrams, unigrams_reference)
    scaff = sorted(scaff.items(), key=lambda k: k[1])
    return scaff


def compare_ex_features(users, users_as_reference=False, reference_users=None, min_length=3, nouns_only=True):
    """
    Calculates features for multiple users and compares the scores for those that they share.

    :param users: A list of UserEx objects for which the features are to be calculated and compared.
    :param users_as_reference: Optional. Default: False. Whether the texts of other users are to be used as the
        reference corpus. If set to Fals, the English Wikipedia dump will be used. If set to True, "all_users" is
        a required argument.
    :param reference_users: Optional. Default: None. Required if "users_as_reference" is set to True. The other users to
        to use as a reference corpus.
    :param min_length: Optional. Default: 3. The minimum amount of alphabetic characters that a feature needs to have.
    :param nouns_only: Optional. Default: True. Whether or not only nouns can be features.
    :return: A dictionary mapping the features found in texts by users from the "users" argument to a list
        of scores for each user, and a second dictionary mapping those features that are shared by at least two users
        to the scores of each user. If a feature was not found for a user, the corresponding score will be 0 (zero).
    """
    comp = defaultdict(lambda: [0] * len(users))
    for i, user in enumerate(users):
        if reference_users.count() == 1 and user in reference_users:
            other_users = reference_users
        else:
            other_users = reference_users.exclude(pk=user.pk)
        scaff = feature_extraction_full_ex([user], users_as_reference=users_as_reference, other_users=other_users,
                                           min_length=min_length, nouns_only=nouns_only)
        for f, s in scaff:
            comp[f][i] = s
    limit = 0 if len(users) == 1 else 1
    shared = {k: v for k, v in comp.items() if sum(1 if x != 0 else 0 for x in v) > limit}
    return comp, shared


if __name__ == "__main__":
    # with open("unigram_counts.p", "rb") as _f:
    #     unigram_counts = pickle.load(_f)
    # with open("bigram_counts.p", "rb") as _f:
    #     bigram_counts = pickle.load(_f)
    # unigram_counts, bigram_counts = get_freqs()
    # unigram_counts, bigram_counts = filter_unigrams_bigrams(unigram_counts, bigram_counts)
    # scaffidi(unigram_counts, bigram_counts, skip_bigrams=True)
    # foo = TweetExIndex.objects.all()
    # foo = list(foo)
    lbs = UserEx.objects.get(screen_name__iexact="lbs")
    ox = UserEx.objects.get(screen_name__iexact="oxfordsbs")
    kellogg = UserEx.objects.get(screen_name__iexact="kelloggschool")
    ross = UserEx.objects.get(screen_name__iexact="michiganross")
    _u = UserEx.objects.all()
    c = compare_ex_features([lbs, ox, kellogg, ross], users_as_reference=True, reference_users=_u)

    _users = UserEx.objects.filter(screen_name__iexact="oxfordsbs")
    _other_users = UserEx.objects.exclude(pk__in=_users.values_list("pk", flat=True))
    # _other_users = UserEx.objects.filter(screen_name__iexact="kelloggschool")
    # users = UserEx.objects.all()
    oxfordsbs = feature_extraction_full_ex(_users, users_as_reference=True, other_users=_other_users)
