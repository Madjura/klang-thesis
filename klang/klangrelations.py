from collections import defaultdict

import math


class KlangRelationsFix(object):
    relations = defaultdict(None, {
        "DATES":
            defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list())))))
    })

    def __init__(self, relations=None):
        if relations:
            self.relations = relations

    def add_unquantified(self, name, x, y, date, no_duplicates=False):
        # relation(x, y) -> talksAbout(school, topic)
        try:
            self.relations["DATES"]["INVERSE"][False][name][y][x].append(date)
            self.relations["DATES"]["REGULAR"][False][name][x][y].append(date)
        except KeyError:
            self.relations["DATES"]["INVERSE"][False][name] = defaultdict(lambda: defaultdict(lambda: list()))
            self.relations["DATES"]["REGULAR"][False][name] = defaultdict(lambda: defaultdict(lambda: list()))
        try:
            exists = self.relations["DATES"]["REGULAR"][False][name][x][y]
        except KeyError:
            exists = False
        if exists and no_duplicates:
            return  # do not add again
        self.relations["DATES"]["REGULAR"][False][name][x][y].append(date)
        self.relations["DATES"]["INVERSE"][False][name][y][x].append(date)

    def add_quantified(self, name, x, y, value, date):
        value = float(value)
        if math.isnan(value):
            return
        # relation(x, y, value) -> hasCitationsInTopic(author, topic, num)
        try:
            self.relations["DATES"]["INVERSE"][True][name][y][x].append((date, value))
        except KeyError:
            self.relations["DATES"]["INVERSE"][True][name] = defaultdict(lambda: defaultdict(lambda: list()))
            self.relations["DATES"]["REGULAR"][True][name] = defaultdict(lambda: defaultdict(lambda: list()))
        self.relations["DATES"]["REGULAR"][True][name][x][y].append((date, value))
        self.relations["DATES"]["INVERSE"][True][name][y][x].append((date, value))
