import pickle
from ast import literal_eval
from collections import defaultdict
from copy import deepcopy

import dill

from common.util import default_to_regular
from klang.util import num_associated_keyword_all, debut_keyword


def _get_score_mapping(scores):
    score_mapping = {
        "isSuper_True": defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list()))),
        "isSuper_False": defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list()))),
        "isSub_True": defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list()))),
        "isSub_False": defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list())))
    }
    for score, kw1, kw2, date, relation in scores:
        if score < 0:
            score_mapping[f"isSuper_{date}"][kw1][kw2][date].append(score)
            # TODO: EXPERIMENTAL
            # score_mapping[f"isSuper_{date}"][kw2][kw1][date].append(score)
        else:
            score_mapping[f"isSub_{date}"][kw1][kw2][date].append(score)
            # TODO: EXPERIMENTAL
            # score_mapping[f"isSub_{date}"][kw2][kw1][date].append(score)
    return score_mapping


def _find_conflicts(input_rel):
    input_rel = default_to_regular(input_rel)
    conflicts = []
    opposites = {
        "isSuper_True": "isSub_True",
        "isSuper_False": "isSub_False",
        "isSub_True": "isSuper_True",
        "isSub_False": "isSuper_False"
    }
    for relation in ["isSuper_True", "isSuper_False", "isSub_True", "isSub_False"]:
        try:
            # TODO: jan 9 2020 check if correct
            d = deepcopy(list(input_rel["DATES"]["REGULAR"][False][relation].items()))
            # d = input_rel["DATES"]["REGULAR"][False][relation].items()
        except KeyError:
            continue
        for kw1, connected in d:
            connected = connected.keys()
            for kw2 in connected:
                try:
                    connected_connected = input_rel["DATES"]["REGULAR"][False][relation][kw2]
                    if kw1 in connected_connected:
                        conflicts.append((kw1, kw2, relation))
                    # TODO: EXPERIMENTAL, NOT NECESSARILY CORRECT AHHHHHH
                    opposite = opposites[relation]
                    connected_connected = input_rel["DATES"]["REGULAR"][False][opposite][kw2]
                    if kw1 in connected_connected:
                        conflicts.append((kw1, kw2, opposite))
                except KeyError:
                    continue
    return conflicts


def break_conflicts(scores, input_rel, debuts_simple, _debug=True):
    """
    Finds conflicts in the relations, e.g. x is superarea of y and y is superarea of x, and resolves them.
    The resolution is performed by checking for two new relations: "contributesTo" and "relatedEquivalent".
    If a keyword x has a higher score for the "isSuper" relation, is connected to more entities and is older than the
    other keyword y a "broaderGeneric" relation is inferred. If it is not connected to more entities and older then a
    "contributesTo" relation is inferred instead.

    :param scores: The score mapping, mapping relations to their score, as calculated by the "get_score_mapping()"
        function.
    :param input_rel:
    :param debuts_simple:
    :param _debug:
    :return:
    """
    # find conflicting relations, i.e. X is superarea of Y and X is subarea of Y
    conflicts = _find_conflicts(input_rel)
    score_map = _get_score_mapping(scores)
    conflicts = sorted(conflicts, key=lambda k: (k[0], k[1], k[2]))
    conflicts = list(zip(*[iter(conflicts)] * 2))
    broader_generic = []
    contribues_to = []
    conflict_remove = []

    for i, (t1, _) in enumerate(conflicts[::2]):
        i *= 2  # get actual index
        # 1 and 4 should be same, 2 and 3 should be same (probably?)
        kw1, kw2, _ = t1
        kw1_super_date = score_map["isSuper_True"][kw1][kw2][True]
        kw1_super = score_map["isSuper_False"][kw1][kw2][False]

        kw2_super_date = score_map["isSuper_True"][kw2][kw1][True]
        kw2_super = score_map["isSuper_False"][kw2][kw1][False]

        kw1_super_score = abs(sum(x for x in kw1_super_date + kw1_super))
        kw2_super_score = abs(sum(x for x in kw2_super_date + kw2_super))

        diff = kw1_super_score - kw2_super_score

        debut_x = debut_keyword(kw1, input_rel, debuts_simple=debuts_simple)
        debut_y = debut_keyword(kw2, input_rel, debuts_simple=debuts_simple)
        connected_x = num_associated_keyword_all(kw1, input_rel)
        connected_y = num_associated_keyword_all(kw2, input_rel)
        if diff > 0:  # kw1 dominates, kw1 is super
            if connected_x > connected_y and (debut_x is None and debut_y is None or debut_x <= debut_y):
                if _debug:
                    print(f"{kw1} ({debut_x}) is super-area of {kw2} ({debut_y})")
                broader_generic.append((kw1, kw2))
                conflict_remove.append((kw2, kw1))  # remove all where kw2 is super of kw1
            else:
                if _debug:
                    print(f"{kw1} ({debut_x}) contributes to {kw2} ({debut_y})")
                contribues_to.append((kw1, kw2))
                conflict_remove.append((kw1, kw2))  # remove all where kw1 is super of kw2
        elif diff < 0:  # kw2 dominates, kw2 is super
            if connected_y > connected_x and (debut_y is None and debut_x is None or debut_y <= debut_x):
                if _debug:
                    print(f"{kw2} ({debut_y}) is super-area of {kw1} ({debut_x})")
                broader_generic.append((kw2, kw1))
                conflict_remove.append((kw1, kw2))  # remove all where kw1 is super of kw2
            else:
                if _debug:
                    print(f"{kw2} ({debut_y}) contributes to {kw1} ({debut_x})")
                contribues_to.append((kw2, kw1))
                conflict_remove.append((kw2, kw1))  # remove all where kw2 is super of kw2
        else:  # oh dear god no
            # print(f"if this ever prints i might have a mental breakdown: conflict scores are identical")
            # i knew it would happen eventually
            # m-m-m-maxi conflict breaker!
            if connected_x > connected_y:
                # kw1 dominates
                if _debug:
                    print(f"{kw1} ({debut_x}) is super-area of {kw2} ({debut_y})")
                broader_generic.append((kw1, kw2))
                conflict_remove.append((kw2, kw1))
            elif connected_x < connected_y:
                # kw2 dominates
                if _debug:
                    print(f"{kw2} ({debut_y}) is super-area of {kw1} ({debut_x})")
                broader_generic.append((kw2, kw1))
                conflict_remove.append((kw1, kw2))
            else:
                # god why
                if debut_x is not None and debut_y is not None:
                    if debut_x > debut_y:
                        # x contributes to y
                        if _debug:
                            print(f"{kw1} ({debut_x}) contributes to {kw2} ({debut_y})")
                        contribues_to.append((kw1, kw2))
                        conflict_remove.append((kw2, kw1))
                    elif debut_x < debut_y:
                        # y contributes to x
                        if _debug:
                            print(f"{kw2} ({debut_y}) contributes to {kw1} ({debut_x})")
                        contribues_to.append((kw2, kw1))
                        conflict_remove.append((kw1, kw2))
                    else:
                        # why does this keep happening
                        first, second = sorted([kw1, kw2])
                        if kw1 == second:
                            kw1, kw2 = second, first
                            debut_x, debut_y = debut_y, debut_x
                        if _debug:
                            print(f"{kw1} ({debut_x}) contributes to {kw2} ({debut_y})")
                        contribues_to.append((kw1, kw2))
                        conflict_remove.append((kw2, kw1))
                elif debut_x is not None:
                    if _debug:
                        print(f"{kw1} ({debut_x}) contributes to {kw2} ({debut_y})")
                    contribues_to.append((kw1, kw2))
                    conflict_remove.append((kw2, kw1))
                elif debut_y is not None:
                    if _debug:
                        print(f"{kw2} ({debut_y}) contributes to {kw1} ({debut_x})")
                    contribues_to.append((kw1, kw2))
                    conflict_remove.append((kw2, kw1))
    # print(conflicts)
    return broader_generic, contribues_to, conflict_remove


if __name__ == "__main__":
    # debug()
    # _p = "/home/madjura/PycharmProjects/klang/klang/scores/ALL_KEYWORDS(books_500)_scores.txt"
    # _r = "/home/madjura/PycharmProjects/klang/klang/RELATIONS_books_500.p"

    # _p = "/home/madjura/PycharmProjects/klang/klang/scores/ALL_KEYWORDS(scp_min)_scores.txt"
    # _r = "/home/madjura/PycharmProjects/klang/klang/RELATIONS_scp_min.p"

    # _p = "/home/madjura/PycharmProjects/klang/klang/scores/ALL_KEYWORDS(scp_min_halfway)_scores.txt"
    # _r = "/home/madjura/PycharmProjects/klang/klang/RELATIONS_scp_min_halfway.p"

    # _p = "/home/madjura/PycharmProjects/klang/klang/scores/ALL_KEYWORDS(books_500_experiment)_scores.txt"
    # _r = "/home/madjura/PycharmProjects/klang/klang/RELATIONS_books_500_experiment.p"

    # _p = "/home/madjura/PycharmProjects/klang/klang/scores/ALL_KEYWORDS(books_500_experiment_date)_scores.txt"
    # _r = "/home/madjura/PycharmProjects/klang/klang/RELATIONS_books_500_experiment_date.p"

    _p = "/home/madjura/PycharmProjects/klang/klang/scores/ALL_KEYWORDS(books_500_experiment_dateFIX)_scores.txt"
    _r = "/home/madjura/PycharmProjects/klang/klang/RELATIONS_books_500_experiment_dateFIX.p"

    with open(_p, "r") as f:
        lines = f.readlines()
    _scores = [literal_eval(line.strip()) for line in lines]

    with open(_r, "rb") as f:
        _input_rel = dill.load(f)

    # noinspection PyTypeChecker
    _mapping = _get_score_mapping(_scores)
    _conflicts = _find_conflicts(_input_rel)
    # break_conflicts(_conflicts, _mapping, _input_rel)
