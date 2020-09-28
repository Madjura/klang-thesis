import pickle

from django.db import transaction

from titaness import setup

setup()
from dataapp.models import TweetEx, UserEx


def dump_tweets():
    t = TweetEx.objects.all().select_related("user")
    t = list(t)
    print(t)
    with open("tweets_all.p", "wb") as f:
        pickle.dump(t, f)
    u = UserEx.objects.all()
    u = list(u)
    with open("users_all.p", "wb") as f:
        pickle.dump(u, f)


def load_dump():
    with open("users_all.p", "rb") as f:
        u = pickle.load(f)
    for uu in u:
        uu.save()
    print("ALL USERS SAVED")
    print("-----------------------")
    with open("tweets_all.p", "rb") as f:
        d = pickle.load(f)
    print(d)
    t = TweetEx.objects.all()
    print(t)
    with transaction.atomic():
        for i, t in enumerate(d):
            print(f"-- Creating {i+1} out of {len(d)} --")
            t.save()
    t = TweetEx.objects.all()
    print(t)


if __name__ == "__main__":
    # dump_tweets()
    load_dump()
