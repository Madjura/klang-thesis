import json
import pickle
from collections import defaultdict
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
from dateutil.relativedelta import relativedelta

from cluster.tfidf import cluster_tweets_all
from cluster.tfidf_ex import cluster_tweets_external, assign_kws_to_tweets_external
from common.util import default_to_regular
from klang.klang_algorithm import init_klang
from klang.klangrelations import KlangRelationsFix
from klangapp.models import PreprocessedText, KlangInput, KlangOutput
from titaness import setup

setup()
from django.core.exceptions import ObjectDoesNotExist

from spikeapp.models import SpikeModel, SpikeRange

from dataapp.models import UserEx, TweetEx
from spike.spike_algorithm import spike4range


def create_models(relevant):
    for i, user in enumerate(relevant):
        print(f"--- Processing user {user} ({i + 1} out of {len(relevant)}) ---")
        others = set(relevant)
        others.remove(user)
        others_regex = "(" + "|".join(others) + ")"
        print(others_regex)
        others = UserEx.objects.filter(screen_name__iregex=others_regex).values_list("screen_name", flat=True)
        SpikeModel.objects.filter(name=f"THESIS:{user}").delete()
        try:
            m = SpikeModel.objects.get(name=f"THESIS:{user}")
            continue
        except ObjectDoesNotExist:
            pass
        try:
            spike4range(f"THESIS:{user}", [UserEx.objects.get(screen_name__iexact=user).screen_name], others, 7, 0)
        except ObjectDoesNotExist:
            continue


def create_klang_input(relevant, limit=3):
    """
    Creates KlangInput for spIke model.
    :param relevant:
    :param limit:
    :return:
    """
    relations = KlangRelationsFix()
    kw2user = defaultdict(lambda: set())
    for user in relevant:
        # create_models(relevant)
        try:
            m = SpikeModel.objects.get(name=f"THESIS:{user}")
        except ObjectDoesNotExist:
            continue
        ranges = SpikeRange.objects.filter(model=m)
        for r in ranges:
            d, scores = list(r.scores.items())[0]
            d = d.split(" - ")[1]
            kws = [x["network"] for x in scores[:limit]]
            for kw in kws:
                kw2user[kw].add(user)
                relations.add_unquantified("hasKeyword", f"{user}-{d}", kw, datetime.strptime(d, "%d/%m/%Y").year)
    x = [kw for kw, users in kw2user.items() if len(users) > 1]
    relations.relations = default_to_regular(relations.relations)
    with open("KLANG_SPIKE_TITANESS.p", "wb") as f:
        pickle.dump(relations.relations, f)


def tfidf_kws(relevant):
    users_regex = "(" + "|".join(relevant) + ")"
    users = UserEx.objects.filter(screen_name__iregex=users_regex).values_list("name", flat=True)
    cluster_tweets_all(users=users)


def assign_kws(users, name="kws-titaness-thesis", do_old=True):
    twitter_texts = []
    clusters = []
    for i, user in enumerate(users):
        print(i + 1, len(users), f"Clustering Tweets for user {user}.")
        # TODO: allow picking date range
        try:
            text = PreprocessedText.objects.filter(name=user).latest("end")
        except ObjectDoesNotExist:
            continue
        twitter_texts.append(text)
        if do_old:
            c = cluster_tweets_external(text)
            clusters.append(c)
    assign_kws_to_tweets_external(clusters, name)


def klang_thesis(name="kws-titaness-thesis"):
    klang_input = KlangInput.objects.get(name=name)
    name = klang_input.name
    relations = klang_input.model
    r = init_klang(relations.relations, name, all_keywords=True)
    relations = r.relations
    relations = default_to_regular(relations)
    KlangOutput.objects.create(klang_input=klang_input, relations=relations)


def klang_thesis_output(name="kws-titaness-thesis"):
    o = KlangOutput.objects.get(klang_input__name=name)
    d = o.relations
    print(o)
    d = default_to_regular(d)
    j = json.dumps(d)
    with open("kws-titaness-thesis-output.json", "w") as f:
        f.write(j)


def klang_spike_fix_thesis_output(name="kws-spike-thesis-fix"):
    with open("klang_spike-klang-fix-0408.p", "rb") as f:
        d = pickle.load(f)
    # d = d.relations
    d = default_to_regular(d)
    j = json.dumps(d)
    with open("kws-spike-thesis-fix-output.json", "w") as f:
        f.write(j)


def klang_spike_month_thesis_output(name="kws-spike-thesis-month"):
    with open("klang_spike-titaness-month.p", "rb") as f:
        d = pickle.load(f)
    # d = d.relations
    d = default_to_regular(d)
    j = json.dumps(d)
    with open("kws-spike-thesis-month-output.json", "w") as f:
        f.write(j)


def create_models_spike_month(relevant):
    """
    Creates spIke model for monthly timerange.
    :param relevant:
    :return:
    """
    for i, user in enumerate(relevant):
        print(f"--- Processing user {user} ({i + 1} out of {len(relevant)}) ---")
        others = set(relevant)
        others.remove(user)
        others_regex = "(" + "|".join(others) + ")"
        print(others_regex)
        others = UserEx.objects.filter(screen_name__iregex=others_regex).values_list("screen_name", flat=True)
        SpikeModel.objects.filter(name=f"THESIS-MONTH:{user}").delete()
        try:
            m = SpikeModel.objects.get(name=f"THESIS-MONTH:{user}")
            continue
        except ObjectDoesNotExist:
            pass
        try:
            spike4range(f"THESIS-MONTH:{user}", [UserEx.objects.get(screen_name__iexact=user).screen_name], others, 0,
                        1)
        except ObjectDoesNotExist:
            continue


def create_klang_input_spike_month(relevant, limit=3):
    """
    Creates spIke month input for Klang algorithm.
    :param relevant:
    :param limit:
    :return:
    """
    relations = KlangRelationsFix()
    kw2user = defaultdict(lambda: set())
    for user in relevant:
        try:
            m = SpikeModel.objects.get(name=f"THESIS-MONTH:{user}")
        except ObjectDoesNotExist:
            continue
        ranges = SpikeRange.objects.filter(model=m)
        for r in ranges:
            d, scores = list(r.scores.items())[0]
            d = d.split(" - ")[1]
            kws = [x["network"] for x in scores[:limit]]
            for kw in kws:
                kw2user[kw].add(user)
                relations.add_unquantified("hasKeyword", f"{user}-{d}", kw, datetime.strptime(d, "%d/%m/%Y").year)
    x = [kw for kw, users in kw2user.items() if len(users) > 1]
    relations.relations = default_to_regular(relations.relations)
    with open("KLANG_SPIKE_MONTH_TITANESS.p", "wb") as f:
        pickle.dump(relations.relations, f)


def imdb_thesis_output():
    with open("klang_imdb-thesis.p", "rb") as f:
        d = pickle.load(f)
    # d = d.relations
    d = default_to_regular(d)
    j = json.dumps(d)
    with open("imdb-thesis-output.json", "w") as f:
        f.write(j)


def vis():
    """
    Visualizes Tweet frequency over time.
    :return:
    """
    t = TweetEx.objects.filter(user__screen_name__in=_relevant).select_related("user")
    print(t)
    dates = [x.created_at for x in t]
    earliest = min(dates).strftime("%Y-%m-%d")
    latest = max(dates).strftime("%Y-%m-%d")
    users = set(x.user for x in t)
    d = [[len(t), len(users), earliest, latest]]
    df = pd.DataFrame(d, columns=["# Texts", "# Users", "From", "To"])
    print(df.to_latex())
    t = t.order_by("created_at")
    prev_limit = min(dates)
    next_limit = prev_limit + relativedelta(years=+1)
    range2num = {}

    years = t.dates("created_at", "year")
    year2num = {}
    for date in years:
        year = date.year
        year2num[year] = TweetEx.objects.filter(user__screen_name__in=_relevant, created_at__year=year).count()
    freq_df = pd.DataFrame(year2num.items(), columns=["Year", "Count"], index=year2num.keys())
    freq_df.plot(x="Year", y="Count", kind="bar", legend=False)
    plt.show()
    print(freq_df.transpose().to_latex())
    print(t)


if __name__ == "__main__":
    with open("../RELEVANT.txt", "r") as f:
        _relevant = [x.strip() for x in f.readlines()[:-1]]

    # create_klang_input(_relevant)
    # tfidf_kws(_relevant)
    # assign_kws(_relevant)
    # klang_thesis()  # DO NOT RUN AGAIN, SLOW ALSO ALREADY FINISHED
    # klang_thesis_output()
    # klang_spike_fix_thesis_output()
    # klang_spike_month_thesis_output()
    # imdb_thesis_output()

    # CREATE SPIKE MODELS
    create_models(_relevant)
    create_models_spike_month(_relevant)

    # create_klang_input_spike_month(_relevant)

    # klang_spike_fix_thesis_output()
    # klang_spike_month_thesis_output()
    # klang_thesis_output()
    # imdb_thesis_output()
