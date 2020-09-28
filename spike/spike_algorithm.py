import math

from titaness import setup

setup()
from collections import defaultdict
from copy import deepcopy

from dateutil.relativedelta import relativedelta

from common.util import scale2range, default_to_regular
from dataapp.models import TweetEx, UserEx
from feature_extraction.scaffidi import feature_extraction_spike
import datetime

from spikeapp.models import SpikeModel, SpikeRange


def _get_tweets(users, ref_users, spike_start, spike_end, ref_start, ref_end):
    # find all tweets in the spike range, of the user(s)
    tweets_spike = TweetEx.objects.filter(user__screen_name__in=users, created_at__gte=spike_start,
                                          created_at__lt=spike_end)
    # find all reference tweets in the spike range
    ref_tweets_spike = TweetEx.objects.filter(created_at__gte=spike_start, created_at__lt=spike_end)
    # if users are specified, limit reference tweets in spike range to them
    if ref_users:
        ref_tweets_spike = ref_tweets_spike.filter(user__screen_name__in=ref_users)

    # find all tweets in the reference range, of the user(s)
    tweets_old = TweetEx.objects.filter(user__screen_name__in=users, created_at__gte=ref_start,
                                        created_at__lt=ref_end)
    # find all reference tweets in the reference range
    ref_tweets_old = TweetEx.objects.filter(created_at__gte=spike_start, created_at__lt=spike_end)
    # if users are specified, limit reference tweets in reference range to them
    if ref_users:
        ref_tweets_old = ref_tweets_old.filter(user__screen_name__in=ref_users)
    return tweets_spike, ref_tweets_spike, tweets_old, ref_tweets_old


def spike(users: [str], ref_users: [str], spike_start, spike_end, ref_start, ref_end):
    tweets_spike, ref_tweets_spike, tweets_old, ref_tweets_old = _get_tweets(users, ref_users, spike_start, spike_end,
                                                                             ref_start, ref_end)
    if not all(x for x in [tweets_spike, ref_tweets_spike, tweets_old, ref_tweets_old]):
        return [], {}, {}, []
    scaff_spike = feature_extraction_spike(tweets_spike, tweets_old, min_length=0, nouns_only=True)
    scaff_ref = feature_extraction_spike(ref_tweets_spike, ref_tweets_old, min_length=0, nouns_only=True)

    features_spike = set(x[0] for x in scaff_spike)
    features_reference = set(x[0] for x in scaff_ref)
    shared = features_spike.intersection(features_reference)

    rank_spike = {term: i for i, (term, _score) in enumerate(scaff_spike)}
    rank_ref = {term: i for i, (term, _score) in enumerate(scaff_ref)}

    try:
        total_min = min((min(rank_spike.values()), min(rank_ref.values())))
    except ValueError:
        total_min = 0  # happens when there is only one aspect
    try:
        total_max = max((max(rank_spike.values()), max(rank_ref.values())))
    except ValueError:
        total_max = 0  # happens when there is only one aspect

    rank_spike = {k: scale2range(total_min, total_max, 0, 100, v) for k, v in rank_spike.items() if k in shared}
    rank_ref = {k: scale2range(total_min, total_max, 0, 100, v) for k, v in rank_ref.items() if k in shared}

    rank_changes = {term: rank_ref[term] - rank_spike[term] for term in shared}
    rank_changes = sorted(rank_changes.items(), key=lambda k: k[1], reverse=True)

    return rank_changes, rank_spike, rank_ref, [(x, abs(y)) for x, y in scaff_spike]


def spike_setup(name, users: [str], ref_users: [str], days=7, months=0):
    tweets = TweetEx.objects.filter(user__screen_name__in=users)
    t = TweetEx.objects.all().select_related("user").values_list("user__screen_name", flat=True)
    t = set(t)
    dates = tweets.values_list("created_at", flat=True).distinct()
    earliest = min(dates)
    latest = max(dates)
    spike_start = earliest  # beginning of the relevant range
    if days:
        d = datetime.timedelta(days=days)
    else:
        d = relativedelta(months=+months)
    model, created = SpikeModel.objects.get_or_create(name=name)
    if not created:
        model.delete()  # TODO: allow updating the model by creating only relevant ranges
        model = SpikeModel.objects.create(name=name)
    if ref_users:
        ref_users_model = UserEx.objects.filter(screen_name__in=ref_users)
    else:
        ref_users_model = UserEx.objects.all()
        ref_users = ref_users_model.values_list("screen_name", flat=True).distinct()
    model.reference.add(*ref_users_model)
    return spike_start, latest, ref_users, model, d


def spike4shift(name, users, days=7, months=0):
    spike_start, latest, ref_users, model, d = spike_setup(name, users, [], days, months)
    i = 0
    while spike_start < latest:
        i += 1


def spike4range(name, users: [str], ref_users: [str], days=7, months=0, pr=None):
    spike_start, latest, ref_users, model, d = spike_setup(name, users, ref_users, days, months)
    rank_changes_, rank_spike_, rank_ref_, scaff_spike_ = [], {}, {}, []

    i = 0
    j = 0

    data_format = defaultdict(lambda: defaultdict(lambda: dict()))
    terms = set()

    while spike_start < latest:
        i += 1
        end = spike_start + d
        spike_end = end  # end of the relevant range, start + timedelta
        # ref_start = earliest  # start at the very beginning, always  # TODO: this doesnt work very well
        ref_start = spike_start - d  # get the previous date range   # TODO: this works better
        ref_end = spike_start  # go from the earliest to the beginning of the range
        # TODO: changed ref_users to ref_users_model, seems like thats how it should be
        if days < 0 or months < 0:
            spike_start, spike_end = spike_end, spike_start
            ref_start, ref_end = ref_end, ref_start
        if pr is not None:
            pr.set_progress(1, 1, description=f"spike from {spike_start.strftime('%d/%m/%Y')} to {spike_end.strftime('%d/%m/%Y')}.")
        rank_changes, rank_spike, rank_ref, scaff_spike = spike(users, ref_users, spike_start, spike_end, ref_start,
                                                                ref_end)
        same_change = set(x[0] for x in rank_changes).intersection(set(x[0] for x in rank_changes_))
        if not same_change:
            j += 1

        for term, score in scaff_spike:
            terms.add(term)
            data_format[(spike_start, spike_end)][term] = {"network": term, "MAU": score}

        same_spike = set(rank_spike.keys()).intersection(rank_spike_.keys())
        same_ref = set(rank_ref.keys()).intersection(rank_ref_.keys())
        same_scaff = set(x[0] for x in scaff_spike).intersection(set(x[0] for x in scaff_spike_))
        # save to db, TODO
        if days < 0 or months < 0:
            spike_start = ref_end
        else:
            spike_start = end  # next range starts where the previous one ended
        rank_changes_ = rank_changes
        rank_spike_ = rank_spike
        rank_ref_ = rank_ref
        scaff_spike_ = scaff_spike
    print("--- SPIKE ALGORITHM FINISHED ---")
    if pr is not None:
        pr.set_progress(1, 1, "Formatting spike data")
    data_format_out = deepcopy(data_format)
    for spike_range, term_dicts in data_format.items():
        existing = set(term_dicts.keys())
        missing = terms.difference(existing)
        for t in missing:
            data_format_out[spike_range][t] = {"network": t, "MAU": 0}
    print("--- DATA FORMAT FINISHED ---")
    if pr is not None:
        pr.set_progress(1, 1, "Saving spike to DB")
    data_format_out = default_to_regular(data_format_out)
    for spike_range, item_dicts in data_format_out.items():
        start, end = spike_range
        start_val = start.strftime("%d/%m/%Y")
        end_val = end.strftime("%d/%m/%Y")
        formatted_dict = {f"{start_val} - {end_val}": list(item_dicts.values())}
        print("--- TRYING TO SAVE SPIKE ---")
        try:
            SpikeRange.objects.create(start=start, end=end, scores=formatted_dict, model=model)
        except Exception as e:
            print("FUCK")
            print(e)
