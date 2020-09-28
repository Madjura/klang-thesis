import os
import pickle
import sys
import time
from collections import defaultdict
from copy import deepcopy

import dill
import math
import numpy as np
import psutil
from scipy import spatial

from common.util import default_to_regular
from klang.cluster import process_clusters, split_cluster_string
from klang.conflicts import break_conflicts
from klang.klangrelations import KlangRelationsFix
from klang.util import debut_keyword, num_associated_keyword

from hurry.filesize import size


def _find_associated_keywords(keyword, input_rel, relation=None, quantified=False, percentile=0.01):
    """
    Finds all keywords that share connections to common elements with another keyword.

    :param keyword: The keyword that other keywords need to share a common element with.
    :param input_rel: The input relation data.
    :param relation: Optional. Default: None. The name of the relation that is being considered. If not passed, all
        relations will be considered.
    :param quantified: Optional. Default: False. Only used when "relation" is passed. Specifies whether or not the
        passed relation is quantified or unquantified.
    :param percentile: Optional. Default: 0.01. How many elements the keywords need to share with "keyword" to be
        considered associated. The value represents a percentage, with 0.01 being equivalent to 1%.
    :return: A set of keywords that share a certain number of elements with "keyword".
    """
    # keyword = "deer"
    if relation is None:
        unquantified = list(input_rel["DATES"]["INVERSE"][False].keys())
        try:
            quantified = list(input_rel["DATES"]["INVERSE"][True].keys())
        except KeyError:
            quantified = []
        freq = defaultdict(int)
        total = 0
        for q in [True, False]:
            if q:
                r = quantified
            else:
                r = unquantified
            for relation in r:
                # get everything that "keyword" is connected to by the relation
                try:
                    entities = input_rel["DATES"]["INVERSE"][q][relation][keyword].keys()
                except KeyError:
                    continue  # does not exist for the relation
                total += len(entities)
                for entity in entities:
                    connected = set(input_rel["DATES"]["REGULAR"][q][relation].get(entity, dict()).keys()) - {keyword}
                    for element in connected:
                        freq[element] += 1
        # TODO: CHECK IF THIS MAKES SENSE AHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH
        if not freq:
            return set()
        cond = round(np.percentile(list(freq.values()), percentile))
        # cond = round(percentile * total)
        r = set(x for x in freq.keys() if freq[x] >= cond)
        return r
    try:
        # find all entities that "keyword" is in a relation with
        elements = input_rel["DATES"]["INVERSE"][quantified][relation][keyword].keys()
    except KeyError:
        return []
    freq = defaultdict(int)
    common_keywords = set()
    for element in elements:
        common = input_rel["DATES"]["REGULAR"][quantified][relation][element].keys()
        for candidate in common:
            freq[candidate] += 1
        common_keywords.update(common)
    if not common_keywords:
        return []
    # return common_keywords
    cond = round(np.percentile(list(freq.values()), percentile))
    return set(x for x in freq.keys() if freq[x] >= cond)


def __calc_vec_val(kw, mapping, val, vec, input_rel, relation, kw2, quantified, date, w, debut, gamma, store):
    """
    Calculates the vector value for use in the cosine similarity calculations.

    :param kw:
    :param mapping:
    :param val:
    :param vec:
    :param input_rel:
    :param relation:
    :param kw2:
    :param quantified:
    :param date:
    :param w:
    :param debut:
    :param gamma:
    :param store:
    :return:
    """
    if val is not None:
        vec_val = val
        vec[mapping[kw]] = val
    else:
        irkx, date_kx = num_associated_keyword(kw, input_rel, relation, keyword2=kw2, quantified=quantified)
        if date_kx is None:
            date_kx = [0]
        if date:
            date_kx = [int(x) for x in date_kx]
            for year in date_kx:
                tmp = (year - debut + 1) ** (-gamma)
                w += tmp
        vec_val = irkx * w
        vec[mapping[kw]] = vec_val
        # TODO: kw2 used to be kw - check if correct, should probably be kw2 and not kw?
        kw_m = mapping[kw]
        kw2_m = mapping[kw2]
        relation_m = mapping[relation]
        # store[kw][kw2][quantified][date][relation] = vec_val
        store[kw_m][kw2_m][quantified][date][relation_m] = vec_val
    return vec_val


def __calc_hierarchical_vectors(x_kws, y_kws, x, y, store, quantified, date, x_vec, y_vec, mapping, debuts,
                                relation, input_rel, debuts_simple, gamma=2, _debug=False):
    kws = x_kws | y_kws
    # TODO: DEBUG, investigate why keyerror can happen here

    # TODO: jan 9 2020 PORT
    # TODO: jan 9 2020 CHECK IF CORRECT TO COMMENT THIS OUT
    # kws.discard(x)
    # kws.discard(y)

    # TODO: jan 9 2020: see if this works
    # x_kws.discard(x)
    # x_kws.discard(y)
    # y_kws.discard(x)
    # y_kws.discard(y)

    for kw in kws:
        try:
            kw_m = mapping[kw]
            x_m = mapping[x]
            y_m = mapping[y]
            relation_m = mapping[relation]
        except KeyError:
            continue

        # x_val = store[kw][x][quantified][date][relation]
        # y_val = store[kw][y][quantified][date][relation]

        x_val = store.get(kw_m, {}).get(x_m, {}).get(quantified, {}).get(date, {}).get(relation_m, None)
        y_val = store.get(kw_m, {}).get(y_m, {}).get(quantified, {}).get(date, {}).get(relation_m, None)

        # x_val = None
        # y_val = None
        if x_val is not None and y_val is not None:
            x_vec[mapping[kw]] = x_val
            y_vec[mapping[kw]] = y_val
            continue
        w_kx = 0 if date else 1
        w_ky = 0 if date else 1

        # TODO: used to be -1, PROBABLY wrong?
        debut_k = None
        if date and (x_val is None or y_val is None):
            debut_k = debuts[kw][relation][quantified]
            if debut_k is None:
                # removed relation from this call, should always use default hasKeyword
                debut_k = debut_keyword(kw, input_rel, debuts_simple=debuts_simple)
                # TODO: check why this can happen, was for scp
                if debut_k is None:
                    continue
                debuts[kw][relation][quantified] = debut_k
        if kw in x_kws:
            # x value
            _val = __calc_vec_val(kw, mapping, x_val, x_vec, input_rel, relation, x, quantified, date, w_kx, debut_k,
                                  gamma, store)
        if kw in y_kws:
            # y value
            _val = __calc_vec_val(kw, mapping, y_val, y_vec, input_rel, relation, y, quantified, date, w_ky, debut_k,
                                  gamma, store)


# was "talksAbout"
def _infer_hierarchical(x, y, input_rel, relation_name="hasKeyword", threshold=0.35, threshold_quantified=0.3,
                        threshold_date=0.2, quantified=False, date=False, store=None, debuts=None, debuts_simple=None,
                        mapping=None, min_shared=0.01):
    if x == y:
        return [], []
    if quantified:
        threshold = threshold_quantified
    if date:
        threshold = threshold_date
    associated_keywords_x = _find_associated_keywords(x, input_rel, relation_name, quantified=quantified,
                                                      percentile=min_shared)
    associated_keywords_y = _find_associated_keywords(y, input_rel, relation_name, quantified=quantified,
                                                      percentile=min_shared)
    if not associated_keywords_x or not associated_keywords_y:
        return [], []
    irxy, date_xy = num_associated_keyword(x, input_rel, relation_name, keyword2=y, quantified=quantified)
    iryx, date_yx = num_associated_keyword(y, input_rel, relation_name, keyword2=x, quantified=quantified)
    irxx, date_xx = num_associated_keyword(x, input_rel, relation_name, keyword2=x, quantified=quantified)
    iryy, date_yy = num_associated_keyword(y, input_rel, relation_name, keyword2=y, quantified=quantified)

    if date:
        date_xy = [int(x) for x in set(date_xy)]
        date_yx = [int(x) for x in set(date_yx)]
        date_xx = [int(x) for x in set(date_xx)]
        date_yy = [int(x) for x in set(date_yy)]
        # removed relation from both debut calls, should always use "hasKeyword" as default
        debut_x = debut_keyword(x, input_rel, debuts_simple=debuts_simple)
        debut_y = debut_keyword(y, input_rel, debuts_simple=debuts_simple)
        if debut_x is None or debut_y is None:
            return [], []  # this happens when for some reason no date is known for a keyword
        w_xy = 0
        for year in date_xy:
            if not math.isnan(year):
                w_xy += (year - debut_x + 1) ** (-2)
        w_yx = 0
        for year in date_yx:
            if not math.isnan(year):
                w_yx += (year - debut_y + 1) ** (-2)
        w_xx = 0
        for year in date_xx:
            if not math.isnan(year):
                w_xx += (year - debut_x + 1) ** (-2)
        w_yy = 0
        for year in date_yy:
            if not math.isnan(year):
                w_yy += (year - debut_y + 1) ** (-2)
    else:
        w_xy, w_yx, w_xx, w_yy = 1, 1, 1, 1
    try:
        left_half = (((irxy * w_xy) / (irxx * w_xx)) - ((iryx * w_yx) / (iryy * w_yy)))
    except ZeroDivisionError:
        return [], []  # TODO: find out why this happens - in second loop iteration, probably because subs/supers were removed
    # mapping dictionary goes both ways, half of the length of it is the length of the vector
    x_vector = np.zeros((int(len(mapping) / 2),))
    y_vector = np.zeros((int(len(mapping) / 2),))

    if x == "multimodaler" and y == "über unser":
        print("!")
    __calc_hierarchical_vectors(associated_keywords_x, associated_keywords_y, x, y, store, quantified, date, x_vector,
                                y_vector, mapping, debuts, relation_name, input_rel, debuts_simple)
    dist = spatial.distance.cosine(x_vector, y_vector)
    cos = 1 - dist
    score = cos * left_half
    # print("NOT: ", x, y, relation_name, left_half, cos)
    supers = []
    subs = []
    if abs(score) >= threshold:
        if score < 0:
            supers.append((score, x, y, date, relation_name))
            # print(f"---> {x} is super-area of {y} ({left_half}, {cos}, {len(x_vector)})")
        else:
            # print(f"---> {x} is sub-area of {y} ({left_half}, {cos}, {len(x_vector)})")
            subs.append((score, x, y, date, relation_name))
    else:
        # if relation_name == "hasSuperArea" or relation_name == "hasSubArea":
        # print("~~~~~", (score, left_half, cos, x, y, relation_name))
        pass
    save_vec = False
    if save_vec:
        with open(f"x_vec_{x}.p", "wb") as f:
            pickle.dump(x_vector, f)
        with open(f"y_vec_{y}.p", "wb") as f:
            pickle.dump(y_vector, f)
    return supers, subs


def _super_concepts(kw, date, input_rel, relation_name=None):
    if not relation_name:
        relation_name = f"isSuper_{date}"
    try:
        supers = set(input_rel["DATES"]["INVERSE"][False][relation_name][kw].keys())
    except KeyError:
        return set()
    return supers


def _sibling_concepts(kw, date, quantified, input_rel, relation_name=None):
    if not relation_name:
        relation_name = f"isSuper_{date}"
    # get supers of kw
    supers = _super_concepts(kw, date, input_rel)
    # then find all sub-concepts of each super element of kw - these are the siblings
    siblings = []
    for super_kw in supers:
        subs = input_rel["DATES"]["REGULAR"][quantified][relation_name][super_kw].keys()
        siblings.extend(subs)
    try:
        siblings = set(siblings)
        siblings.remove(kw)
    except KeyError:
        pass
    finally:
        siblings = set(siblings)
    return siblings


def _infer_semantic(x, y, input_rel, quantified, date, mapping, relation, min_shared, store, debuts, debuts_simple):
    supers_x = _super_concepts(x, date, input_rel)
    siblings_x = _sibling_concepts(x, date, quantified, input_rel)
    supers_y = _super_concepts(y, date, input_rel)
    siblings_y = _sibling_concepts(y, date, quantified, input_rel)

    x_vector = np.zeros((len(mapping) // 2,))
    y_vector = np.zeros((len(mapping) // 2,))
    associated_keywords_x = _find_associated_keywords(x, input_rel, relation, quantified=quantified,
                                                      percentile=min_shared)
    associated_keywords_y = _find_associated_keywords(y, input_rel, relation, quantified=quantified,
                                                      percentile=min_shared)
    associated_keywords_x = set(associated_keywords_x)
    associated_keywords_y = set(associated_keywords_y)
    __calc_hierarchical_vectors(associated_keywords_x, associated_keywords_y, x, y, store, quantified, date, x_vector,
                                y_vector, mapping, debuts, relation, input_rel, debuts_simple)

    x_vector_super = np.zeros((len(mapping) // 2,))
    y_vector_super = np.zeros((len(mapping) // 2,))
    __calc_hierarchical_vectors(supers_x, supers_y, x, y, store, quantified, date, x_vector_super,
                                y_vector_super, mapping, debuts, relation, input_rel, debuts_simple)

    x_vector_sibling = np.zeros((len(mapping) // 2,))
    y_vector_sibling = np.zeros((len(mapping) // 2,))
    __calc_hierarchical_vectors(siblings_x, siblings_y, x, y, store, quantified, date, x_vector_sibling,
                                y_vector_sibling, mapping, debuts, relation, input_rel, debuts_simple)
    # TODO: jan 9 2020, port + check if correct, if else is new
    try:
        cos = 1 - spatial.distance.cosine(x_vector, y_vector)
    except FloatingPointError:
        cos = 0
    # TODO: jan 9 2020, port + check if correct, if else is new
    try:
        cos_super = 1 - spatial.distance.cosine(x_vector_super, y_vector_super)
    except FloatingPointError:
        cos_super = 0
    if math.isnan(cos_super):
        return None
    # TODO: jan 9 2020, port + check if correct, if else is new
    try:
        cos_sibling = 1 - spatial.distance.cosine(x_vector_sibling, y_vector_sibling)
    except FloatingPointError:
        cos_sibling = 0
    if math.isnan(cos_sibling):
        return None

    score = cos / (max(cos_super, cos_sibling) + 1)
    # print(score)
    return score


def infer_relationships(x, y, input_rel, loop_index, store=None, mapping=None, debuts=None, debuts_simple=None,
                        min_shared=None):
    unquantified = input_rel["DATES"]["INVERSE"][False].keys()
    nondate_cond = []
    date_cond = []
    if loop_index > 0:
        try:
            r1 = input_rel["DATES"]["REGULAR"][False]["isSuper_True"][x].get(y, False)
        except KeyError:
            r1 = False
        r2 = input_rel["DATES"]["REGULAR"][False]["isSuper_False"][x].get(y, False)
        try:
            r3 = input_rel["DATES"]["REGULAR"][False]["isSub_True"][x].get(y, False)
        except KeyError:
            r3 = False
        r4 = input_rel["DATES"]["REGULAR"][False]["isSub_False"][x].get(y, False)

        try:
            r5 = input_rel["DATES"]["INVERSE"][False]["isSuper_True"][x].get(y, False)
        except KeyError:
            r5 = False
        r6 = input_rel["DATES"]["INVERSE"][False]["isSuper_False"][x].get(y, False)
        try:
            r7 = input_rel["DATES"]["INVERSE"][False]["isSub_True"][x].get(y, False)
        except KeyError:
            r7 = False
        r8 = input_rel["DATES"]["INVERSE"][False]["isSub_False"][x].get(y, False)

        date_cond = [r1, r3, r5, r7]
        nondate_cond = [r2, r4, r6, r8]
    try:
        quantified = input_rel["DATES"]["INVERSE"][True].keys()
    except KeyError:
        # happens when no quantified relations exist
        quantified = []
    supers = []
    subs = []
    semantics = []
    for relation in unquantified:
        if loop_index <= 0 or (loop_index > 0 and not any(nondate_cond)):
            supers_new, subs_new = _infer_hierarchical(x, y, input_rel, relation_name=relation,
                                                       quantified=False, store=store, mapping=mapping, debuts=debuts,
                                                       debuts_simple=debuts_simple, min_shared=min_shared)
            supers.extend(supers_new)
            subs.extend(subs_new)

        if loop_index <= 0 or (loop_index > 0 and not any(date_cond)):
            # with date
            supers_new, subs_new = _infer_hierarchical(x, y, input_rel, relation_name=relation,
                                                       quantified=False, date=True, store=store, mapping=mapping,
                                                       debuts=debuts, debuts_simple=debuts_simple,
                                                       min_shared=min_shared)
            supers.extend(supers_new)
            subs.extend(subs_new)

        # dont do it for first loop
        if loop_index > 0:
            semantic_score = _infer_semantic(x, y, input_rel, False, False, mapping, relation, min_shared, store,
                                             debuts, debuts_simple)
            if semantic_score:
                semantics.append((x, y, False, False, semantic_score))
            semantic_score = _infer_semantic(x, y, input_rel, False, True, mapping, relation, min_shared, store, debuts,
                                             debuts_simple)
            if semantic_score:
                semantics.append((x, y, False, True, semantic_score))

    memory_load = psutil.virtual_memory().percent
    if memory_load >= 85:  # 85% ram used
        # reset to not run into memory problems
        store = defaultdict(lambda: defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))))
        debuts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))
        debuts_simple = defaultdict(lambda: None)

    for relation in quantified:
        supers_new, subs_new = _infer_hierarchical(x, y, input_rel, relation_name=relation,
                                                   quantified=True, store=store, mapping=mapping, debuts=debuts,
                                                   debuts_simple=debuts_simple)
        supers.extend(supers_new)
        subs.extend(subs_new)

        # with date
        supers_new, subs_new = _infer_hierarchical(x, y, input_rel, relation_name=relation,
                                                   quantified=True, date=True, store=store, mapping=mapping,
                                                   debuts=debuts, debuts_simple=debuts_simple)
        supers.extend(supers_new)
        subs.extend(subs_new)

        # dont do it for first loop
        if loop_index > 0:
            semantic_score = _infer_semantic(x, y, input_rel, True, False, mapping, relation, min_shared, store,
                                             debuts, debuts_simple)
            if semantic_score:
                semantics.append((x, y, True, False, semantic_score))
            semantic_score = _infer_semantic(x, y, input_rel, True, True, mapping, relation, min_shared, store, debuts,
                                             debuts_simple)
            if semantic_score:
                semantics.append((x, y, True, True, semantic_score))
    return supers, subs, semantics


# noinspection PyDefaultArgument
def _transitive_super(kw, input_rel, checked=set()):
    supers_nondate = _super_concepts(kw, False, input_rel)
    supers_date = _super_concepts(kw, True, input_rel)
    tops = []
    to_check = (supers_nondate | supers_date) - checked
    checked.update(to_check)
    if not to_check:
        if supers_nondate or supers_date:
            return []
        return [kw]  # reached the maximum
    for super_kw in to_check:
        top_kw = _transitive_super(super_kw, input_rel)
        tops.extend(set(top_kw))
    return tops


def _disambiguate(found_clusters, input_rel):
    # found_clusters: clusters that kw2/kkw2 belong to
    # kw2/kkw2 are keywords that are connected to kw
    # kw is potentially ambiguous
    results = []
    for found_cluster in found_clusters:
        if len(found_cluster) < 2:
            continue  # not ambiguous
        # each cluster in "found_cluster" is ambiguous!
        for _cluster_name, cluster_elems in found_cluster:
            freqs = defaultdict(int)
            for e in cluster_elems:
                supers = _transitive_super(e, input_rel)
                # supers_nondate = _super_concepts(e, False, input_rel)
                # supers_date = _super_concepts(e, True, input_rel)
                # supers = supers_nondate | supers_date

                # for each element in the cluster find the highest super-concept
                # count how often it appears
                for s in supers:
                    freqs[s] += 1
            try:
                most_common = [k for k, v in freqs.items() if v == max(freqs.values())]
                # most_common = max(freqs.items(), key=lambda k: k[1])
                results.append((most_common, cluster_elems))
            except ValueError:
                print("NO VALUES: ", cluster_elems)
        break  # enough to look at one ambiguous cluster
    return results


def _all_relations_for_kw(kw, input_rel):
    unquantified = list(input_rel["DATES"]["INVERSE"][False].keys())
    try:
        quantified = list(input_rel["DATES"]["INVERSE"][True].keys())
    except KeyError:
        quantified = []

    relations = []
    for q in [True, False]:
        if q:
            r = quantified
        else:
            r = unquantified
        for relation in r:
            inverse = input_rel["DATES"]["INVERSE"][q][relation].get(kw, dict()).items()
            regular = input_rel["DATES"]["REGULAR"][q][relation].get(kw, dict()).items()
            for kw2 in inverse:
                relations.append(("INVERSE", q, relation, kw2))
            for kw2 in regular:
                relations.append(("REGULAR", q, relation, kw2))
    return relations


def _get_kw_debut(kw, debuts_simple, input_rel, relation="hasKeyword"):
    debut = debuts_simple[kw]
    if debut is None:
        return debut_keyword(kw, input_rel, debuts_simple=debuts_simple, relation=relation)
    return debut


def _replace_relation(input_rel, old_relation, new_kw, old_kw, mapping):
    # TODO: update mapping!
    if new_kw not in mapping:
        next_elem = max([x for x in mapping.keys() if isinstance(x, int)]) + 1
        mapping[new_kw] = next_elem
        mapping[next_elem] = new_kw
    direction, quantified, relation, (kw2, values) = old_relation
    input_rel["DATES"][direction][quantified][relation][old_kw].pop(kw2, None)
    # TODO: check if this if-else block is correct!
    if direction == "INVERSE":
        # remove the regular direction too
        input_rel["DATES"]["REGULAR"][quantified][relation][kw2].pop(old_kw, None)
        input_rel["DATES"]["INVERSE"][quantified][relation][kw2] = defaultdict(lambda: list(), {new_kw: values})
    elif direction == "REGULAR":
        input_rel["DATES"]["INVERSE"][quantified][relation][kw2].pop(old_kw, None)
        input_rel["DATES"]["INVERSE"][quantified][relation][kw2] = defaultdict(lambda: list(), {new_kw: values})
    input_rel["DATES"][direction][quantified][relation][new_kw] = defaultdict(lambda: list(), {kw2: values})


def __score_ambi_relation(relation, disambid_kws, input_rel):
    direction, quantified, relation, (kw2, values) = relation
    try:
        debut_kw2 = debut_keyword(kw2, input_rel, relation=relation, direction="INVERSE", quantified=quantified) or 0
    except KeyError:
        debut_kw2 = debut_keyword(kw2, input_rel, relation=relation, direction="REGULAR", quantified=quantified) or 0
    kw2_relations = _all_relations_for_kw(kw2, input_rel)
    scores = {}
    for old_kw, kw1, cluster_elems, super_elems in disambid_kws:
        try:
            debut_kw1 = debut_keyword(old_kw, input_rel, relation=relation, direction="INVERSE") or 0
        except KeyError:
            debut_kw1 = debut_keyword(old_kw, input_rel, relation=relation, direction="REGULAR") or 0
        debut_diff = abs(debut_kw1 - debut_kw2)  # higher = better
        share_check = [old_kw]
        share_check.extend(cluster_elems)
        share_check.extend(super_elems)
        share_check = set(share_check)
        shared = sum(1 for x in kw2_relations if x[3][0] in share_check)
        scores[kw1] = debut_diff + shared
    scores = sorted(scores.items(), key=lambda k: k[1], reverse=True)
    return scores[0]


def _update_ambi_relations(ambis, input_rel, mapping):
    # ambis is a dictionary in the format: {kw: [( [most common super elements], [elements in cluster] )]
    to_replace = []
    new_kws = []
    for kw, values in ambis.items():
        kw_relations = _all_relations_for_kw(kw, input_rel)
        # TODO: check for duplicates here that have the same super elements
        new_kws = []  # contains all the new, disambid keywords. example: owl (ontology), owl (bird)
        # TODO: remove this after running it again. FOR DEBGUGGING ONLY
        # values = values[0]
        for super_elements, cluster_elems in values:
            if not super_elements:
                cluster_elems = super_elements
            super_elements = sorted(super_elements)
            kw_new = f"{kw} ({','.join(super_elements)})"
            new_kws.append((kw, kw_new, cluster_elems, super_elements))
        new_kws_check = []
        # removing duplicates, which hopefully dont happen
        prev = None
        for i, (old_kw, new_kw, cluster_elems, super_elems) in enumerate(new_kws):
            if i == len(new_kws) - 1 and new_kw != prev:
                new_kws_check.append((old_kw, new_kw, cluster_elems, super_elems))
            for (_, new_kw2, _, _) in new_kws[i + 1:]:
                if new_kw != new_kw2:
                    new_kws_check.append((old_kw, new_kw, cluster_elems, super_elems))
            prev = new_kw
        if len(new_kws_check) < 2:
            # not an ambi keyword after all
            continue
        for relation in kw_relations:
            relation_candidate, _score = __score_ambi_relation(relation, new_kws_check, input_rel)
            print(relation_candidate)
            to_replace.append((relation, relation_candidate, kw))
    for relation, new_kw, old_kw in to_replace:
        _replace_relation(input_rel, relation, new_kw, old_kw, mapping)
        new_kws.append(new_kw)
    return new_kws


def split_ambiguous(keywords, input_rel, min_shared, mapping, store, debuts, debuts_simple):
    unquantified = input_rel["DATES"]["REGULAR"][False].keys()
    try:
        quantified = input_rel["DATES"]["REGULAR"][True].keys()
    except KeyError:
        quantified = []
    ambiguous = []
    for q in [True, False]:
        if q:
            r = quantified
        else:
            r = unquantified
        for j, relation in enumerate(r):
            score_mapping = defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))))
            print(f"--> Processing relation {j + 1} ({relation}) out of {len(r)} <--")
            for i, kw in enumerate(keywords):
                semantics = []
                print(f"-- Ambiguous calc {i + 1} of {len(keywords)} --")
                connected = _find_associated_keywords(kw, input_rel, percentile=min_shared)
                connected.discard(kw)
                date = "_True" in relation
                for k, kw2 in enumerate(connected):
                    print(f"-- Ambi calc for keyword {kw2} ({k + 1} of {len(connected)}) --")
                    for kkw2 in connected:
                        if kw2 == kkw2:
                            continue  # TODO: 16/07/2020 check if makes sense
                        score = score_mapping[kw2][kkw2][q][date][relation] \
                                or score_mapping[kkw2][kw2][q][date][relation]
                        if score is None:
                            score = _infer_semantic(kw2, kkw2, input_rel, q, date, mapping, relation, min_shared, store,
                                                    debuts, debuts_simple)
                        score_mapping[kw2][kkw2][q][date][relation] = score
                        if score is not None and score != 0:
                            semantics.append((kw2, kkw2, q, date, score))
                equivalents, found = process_clusters(semantics, threshold=0, input_rel=input_rel, round_to=2)
                if any(len(x) > 1 for x in found):
                    print("AMBIGUOUS: ", kw, len(found))
                    # for each keyword kw, checks ALL pairs of keywords kw2/kkw2 that are connected to it
                    # does clustering on the connected keywords, using S(x, y) score
                    # if multiple clusters appear then the keyword is ambiguous, potentially
                    # "found" has the found clusters
                    # the kw, the clusters and whether it is quantified are added to the ambiguous list
                    ambiguous.append((kw, found, q))
                    break  # TODO: check if this makes sense
            print("-----------------------------")
    # disambiguated = []
    disambi_process = defaultdict(lambda: list())
    for (kw, clusters, quantified) in ambiguous:
        # kw: ambiguous keyword
        # clusters: found clusters for keywords kw2/kkw2 which are connected to kw
        # kw2 and kkw2 are in SEPARATE clusters
        # here it finds the most suitable (most common) super-concept for each cluster
        disambi_process[kw] = _disambiguate(clusters, input_rel)
        # disambiguated.append((kw, _disambiguate(clusters, input_rel)))

    # with open("disambi.p", "wb") as f:
    #     dill.dump(disambi_process, f)
    # with open("disambi_input_rel.p", "wb") as f:
    #     dill.dump(input_rel, f)
    # with open("ambiguous.p", "wb") as f:
    #     dill.dump(ambiguous, f)

    # after finding the most common super-concepts for each cluster, make new, separated keywords
    new_kws = _update_ambi_relations(disambi_process, input_rel, mapping)
    return new_kws


def merge_similar_keywords(keywords, rel):
    # TODO!
    return []


def _kw_index(input_rel):
    all_relations = list(input_rel["DATES"]["INVERSE"][False].keys())
    relation = "hasKeyword"
    all_keywords = list(input_rel["DATES"]["INVERSE"][False][relation].keys())
    mapping = {}
    i = 0
    for keyword in all_keywords:
        mapping[i] = keyword
        mapping[keyword] = i
        i += 1
    relations_future = ["isSuper_True", "isSuper_False", "isSub_True", "isSub_False", "relatedEquivalent",
                        "broaderGeneric", "contributesTo"]
    all_relations.extend(relations_future)
    for r in all_relations:
        mapping[i] = r
        mapping[r] = i
        i += 1
    return mapping


def _all_kws(input_rel):
    """
    Returns all keywords in the relations.

    :param input_rel: The relation data.
    :return: A list of all keywords.
    """
    kws = list(input_rel["DATES"]["INVERSE"][False]["hasKeyword"].keys())
    return kws


def init_klang(input_relations, out_name, shared_percentile=75, all_keywords=False, halfway=False,
               shared_percentile_ambi=75, keywords_only=None):
    """
    Starts the Klang algorithm.

    :param input_relations: The relation data.
    :param out_name: The identifier for the output file. This name should correspond in some way to the data that was
        used.
    :param shared_percentile: Optional. Default: 5.
    :param all_keywords:
    :param halfway:
    :param shared_percentile_ambi:
    :param keywords_only: Optional. The keywords that are to be considered. This can be used
    :return:
    """
    split_merge = True
    relations = None
    # prev_len = 0
    mapping = _kw_index(input_relations)
    debuts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))
    debuts_simple = defaultdict(lambda: None)
    relations_obj = KlangRelationsFix(input_relations)
    loop_index = -1 if not halfway else 0
    keywords = None
    end_flag = False

    while loop_index < 3 and not end_flag:  # TODO: set it to 2 to capture relatedEquivalent relations
        if all_keywords:
            keywords = _all_kws(input_relations)
        else:
            keywords = keywords_only
        store = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))))
        loop_index += 1
        # prev_len = len(keywords)
        scores = []
        supers_add = []
        subs_add = []
        semantics_add = []
        for j, k in enumerate(keywords):
            if all_keywords:
                print(f"---> PROCESSING KEYWORD {k} ({j + 1} of {len(keywords)}) <---")
                memory_load = psutil.virtual_memory().percent
                if memory_load >= 85:  # 85% ram used
                    # reset to not run into memory problems
                    store = defaultdict(lambda: defaultdict(
                        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))))
                    debuts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: None)))
                    debuts_simple = defaultdict(lambda: None)
            # TODO: check if not passing main_relation makes a difference
            # keywords2 = _find_associated_keywords(k, input_relations, main_relation, min_shared=min_shared)
            keywords2 = _find_associated_keywords(k, input_relations, percentile=shared_percentile)
            for i, k2 in enumerate(keywords2):
                if not all_keywords:
                    print(f"---> CHECKING {k} {k2} ({i + 1} of {len(keywords2)}) <---")
                supers, subs, semantics = infer_relationships(
                    k, k2, input_relations, loop_index, store=store, mapping=mapping, debuts=debuts,
                    debuts_simple=debuts_simple, min_shared=shared_percentile)
                supers_add.extend(supers)
                subs_add.extend(subs)
                semantics_add.extend(semantics)
                # TODO: check if this is needed, probably not? they are added after the loop in the block below
                # for s in supers:
                #     _, kw1, kw2, date, _ = s
                #     relations_obj.add_unquantified(f"isSuper_{date}", kw1, kw2, 0)
                # for s in subs:
                #     _, kw1, kw2, date, _ = s
                #     relations_obj.add_unquantified(f"isSub_{date}", kw1, kw2, 0)
                scores.extend(supers)
                scores.extend(subs)
        # TODO: check if this causes issues - the goal is to purge the store ASAP because it takes A LOT of memory
        if not split_merge:
            store = None
        input_relations = relations_obj.relations
        for s in supers_add:
            _, kw1, kw2, date, _ = s
            relations_obj.add_unquantified(f"isSuper_{date}", kw1, kw2, 0, no_duplicates=True)
            # TODO: CHECK IF THIS CAUSES ISSUES!
            relations_obj.add_unquantified(f"isSub_{date}", kw2, kw1, 0, no_duplicates=True)
        for s in subs_add:
            _, kw1, kw2, date, _ = s
            relations_obj.add_unquantified(f"isSub_{date}", kw1, kw2, 0, no_duplicates=True)
            # TODO: CHECK IF THIS CAUSES ISSUES!
            relations_obj.add_unquantified(f"isSuper_{date}", kw1, kw2, 0, no_duplicates=True)

        # vvv ======= relatedEquivalent BLOCK HERE ========= vvv #
        print("--> RELATEDEQUIVALENT BLOCK <--")
        if loop_index >= 1:
            # with open(f"SEMANTICS_{out_name}.p", "wb") as f:
            #     dill.dump(semantics_add, f)
            print("-> PROCESSING CLUSTERS <-")
            equivalents, _ = process_clusters(semantics_add)
            for l, (c1, c2) in enumerate(equivalents):
                print(f"--> {l + 1} equivalent checks out of {len(equivalents)} <--")
                c1s = list(split_cluster_string(c1))
                c2s = list(split_cluster_string(c2))
                # TODO: 14/07/2020 - this is PROBABLY WRONG it makes ALL keywords relatedEquivalent to each other!
                # only those on the same level should be considered equal
                # if the len of one of them is > 1 then either skip them or do "kw1,kw2,kw3" relatedEquivalent "kw4" and so on
                if len(c1s) > 1 or len(c2s) > 1:
                    continue  # TODO: MAYBE REMOVE THIS CONTINUE
                    # pass
                all_equivs = c1s + c2s
                # print(all_equivs)
                for ll, kw1 in enumerate(all_equivs):
                    kw2s = all_equivs[ll + 1:]
                    for kw2 in kw2s:
                        if kw1 == kw2:
                            continue  # avoid duplicates
                        # remove all incorrect super and sub relations, based on being equivalent
                        try:
                            relations_obj.relations["DATES"]["REGULAR"][False]["isSuper_True"][kw1].pop(kw2, None)
                            relations_obj.relations["DATES"]["REGULAR"][False]["isSub_True"][kw2].pop(kw1, None)
                        except KeyError:
                            # happens when no date relations exist, for data without dates
                            relations_obj.relations["DATES"]["REGULAR"][False]["isSuper_False"][kw1].pop(kw2, None)
                            relations_obj.relations["DATES"]["REGULAR"][False]["isSub_False"][kw2].pop(kw1, None)
                        # add a relation indicating the two keywords are equivalent
                        relations_obj.add_unquantified("relatedEquivalent", kw1, kw2, 0, no_duplicates=True)
                        # TODO: check if correct
                        relations_obj.add_unquantified("relatedEquivalent", kw2, kw1, 0, no_duplicates=True)
        # ^^^ ======= relatedEquivalent BLOCK END ========== ^^^ #

        # vvv ====== CONFLICT BLOCK STARTS HERE ====== vvv #
        print("========= PROCESSING CONFLICT BLOCK =========")
        # calculate broaderGeneric and contributesTo relations
        broader, contributes, remove = break_conflicts(scores, input_relations, debuts_simple)
        for kw1, kw2 in broader:
            relations_obj.add_unquantified("broaderGeneric", kw1, kw2, 0, no_duplicates=True)
        for kw1, kw2 in contributes:
            relations_obj.add_unquantified("contributesTo", kw1, kw2, 0, no_duplicates=True)

        # TODO: also remove contributesTo and broaderGeneric - future iteration might reverse the relation (maybe?)
        for kw1, kw2 in remove:
            # kw1 is NOT a super of kw2, kw2 is NOT a sub of kw1: remove the relations!
            try:
                relations_obj.relations["DATES"]["REGULAR"][False]["isSuper_True"][kw1].pop(kw2, None)
                relations_obj.relations["DATES"]["REGULAR"][False]["isSub_True"][kw2].pop(kw1, None)
            except KeyError:
                # happens when no date relations exist, for data that does not have publication dates available
                pass
            relations_obj.relations["DATES"]["REGULAR"][False]["isSuper_False"][kw1].pop(kw2, None)
            relations_obj.relations["DATES"]["REGULAR"][False]["isSub_False"][kw2].pop(kw1, None)
        input_relations = relations_obj.relations
        # ^^^ ====== CONFLICT BLOCK ENDS HERE ====== ^^^ #

        # r2 = deepcopy(relations_obj.relations)
        # r2 = default_to_regular(r2)
        # relations_file = f"RELATIONS_{loop_index}_{out_name}.p"
        # with open(relations_file, "wb") as f:
        #     dill.dump(r2, f)
        if loop_index < 1:
            continue
        else:
            pass
            # scores = sorted(scores, key=lambda y: y[0])
            # file_name = f"{','.join(keywords)}({out_name})_scores.txt"
            # if all_keywords:
            #     file_name = f"ALL_KEYWORDS({out_name})_scores.txt"
            # with open(os.path.join(scores_path, file_name), "w") as f:
            #     f.write("\n".join([str(x) for x in scores]))

            # relations_obj.relations = default_to_regular(relations_obj.relations)
            # with open(os.path.join(relations_path, relations_file), "wb") as f:
            #     dill.dump(relations_obj.relations, f)
        if split_merge:
            pass
            # TODO: comment back in maybe, but this is slooooooooooooooooooooooooooooooooooooooooooooooooow
            # TODO: 17/07/2020 - for each found cluster, look at elements from cluster, and assign to each newly disambiguated kw the relations that the original shares to the same entitites as the cluster elems
            new_keywords = split_ambiguous(keywords, relations_obj.relations, shared_percentile_ambi, mapping, store,
                                           debuts, debuts_simple)
            # import pprint
            # pprint.pprint(new_keywords)
            # print("___________________________________________")
        else:
            _keywords = merge_similar_keywords(keywords, relations)
        split_merge = not split_merge
    # keywords = filter_not_academic_keywords(keywords, input_relations, relations)
    with open(os.path.join("/home/madjura/PycharmProjects/klang/klang/processed", f"klang_{out_name}.p"), "wb") as f:
        dill.dump(relations_obj.relations, f)
    return relations_obj
