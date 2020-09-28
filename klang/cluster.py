from collections import defaultdict
from copy import deepcopy

import dill

from common.util import default_to_regular
import networkx as nx


def networkx_transitive(clusters):
    g = nx.Graph(clusters)
    foo = [x for x in sorted(nx.connected_components(g), key=len, reverse=True)]
    return foo


def split_cluster_string(cluster_string, ignore=""):
    cluster_string = cluster_string.replace("\n", ";").strip().split(";")
    cluster_string = set([x for x in cluster_string if x and x != ignore])
    return cluster_string


def _transitive_connected(clusters, cluster, processed, depth=0, max_depth=3):
    connected = set()
    out = set()
    for c1, c2 in clusters:
        if c1 == cluster and c2 not in processed:
            connected.add(c2)
        elif c2 == cluster and c1 not in processed:
            connected.add(c1)
    processed.add(cluster)
    for c in connected:
        if depth == max_depth:
            break
        cc = _transitive_connected(clusters, c, processed, depth + 1)
        for elem in cc:
            out.add(elem)
    return out | connected | {cluster}


def _merge_same_level_clusters(clusters, transitive):
    new_clusters = set()
    # clusters is a list of pairs of clusters/nodes that have the same distance
    clusters = sorted(clusters, key=lambda k: (k[0], k[1]))
    for i, (c1, c2) in enumerate(clusters):
        print(f"~~~ MERGING CLUSTER {i + 1} OUT OF {len(clusters)} ~~~")
        # c1_connected = _transitive_connected(clusters, c1, set())

        # c2_connected = _transitive_connected(clusters, c2, set())
        # if c1_connected != c2_connected:
        #     raise Exception("oh dear god please no god why")

        # elems = sorted(c1_connected)

        tmp = [i for i, x in enumerate(transitive) if c1 in x]
        elems = transitive[tmp[0]]
        new_cluster = ";".join(elems) + "\n"
        new_clusters.add((new_cluster, tuple(elems)))
    return new_clusters
    # old stuff, didnt work
    # for c1, c2 in clusters:
    #     c1_connected = []
    #     c2_connected = []
    #     # find all connected to c1 or c2
    #     for c11, c22 in clusters:
    #         # c1 is connected to c22
    #         if c11 == c1 and c22 != c2:
    #             c1_connected.append(c22)
    #         # c11 is connected to c1
    #         elif c22 == c1 and c11 != c2:
    #             c1_connected.append(c11)
    #         # c2 is connected to c22
    #         elif c11 == c2 and c22 != c1:
    #             c2_connected.append(c22)
    #         # c11 is connected to c2
    #         elif c22 == c2 and c11 != c1:
    #             c2_connected.append(c11)
    #     common = set(c1_connected).intersection(set(c2_connected))
    #     if not common:
    #         # the cluster is independent of everything else
    #         c = sorted((c1, c2))
    #         new_cluster = f"({c[0]};{c[1]})"
    #         new_clusters.append((new_cluster, tuple(c)))
    #     else:
    #         # clusters can be merged together
    #     print("!")

    # for i, (c1, c2) in enumerate(clusters):
    #     c1_connected = []
    #     c2_connected = []
    #     for c11, c22 in clusters[i+1:]:
    #         if c11 == c1 or c22 == c1:
    #             c1_connected.append(c11)
    #             c1_connected.append(c22)
    #         if c11 == c2 or c22 == c2:
    #             c2_connected.append(c11)
    #             c2_connected.append(c22)
    #     c1_connected = set(c1_connected)
    #     c2_connected = set(c2_connected)
    #     common = c1_connected.intersection(c2_connected)
    #     common.add(c1)
    #     common.add(c2)
    #     # if not common:
    #     #     new_clusters.append(c1)
    #     #     new_clusters.append(c2)
    #     # else:
    #     if not common:
    #         c = sorted((c1, c2))
    #         new_cluster = f"({c[0]};{c[1]})"
    #         new_clusters.append((new_cluster, tuple(c)))
    #         continue
    #     if len(common) == 1:
    #         print("!")
    #     common = sorted(common)
    #     new_cluster = "(" + ";".join(common) + ")"
    #     new_clusters.append((new_cluster, tuple(common)))
    # new_clusters = sorted(set(new_clusters), key=lambda k: len(k[1]))
    # cluster_fix = []
    # for i, (new_cluster, elems1) in enumerate(new_clusters):
    #     cluster_elements1 = _split_cluster_string(new_cluster, elems1[1])
    #     redundant = False
    #     for new_cluster2, elems2 in new_clusters[i+1:]:
    #         cluster_elements2 = _split_cluster_string(new_cluster2, elems2[1])
    #         if cluster_elements1.issubset(cluster_elements2) or cluster_elements2.issubset(cluster_elements1):
    #             redundant = True
    #             break
    #     if not redundant:
    #         cluster_fix.append((new_cluster, elems1))
    # # return new_clusters
    # return cluster_fix


def num_associated(kw, input_rel):
    associated = []
    unquantified = list(input_rel["DATES"]["INVERSE"][False].keys())
    try:
        quantified = list(input_rel["DATES"]["INVERSE"][True].keys())
    except KeyError:
        quantified = []
    unquantified = [x for x in unquantified if "_True" not in x and "_False" not in x]
    for q in [True, False]:
        if q:
            r = quantified
        else:
            r = unquantified
        for relation in r:
            try:
                associated.extend(input_rel["DATES"]["INVERSE"][q][relation][kw].keys())
            except KeyError:
                kw = kw.replace("\n", ";")
                kws = kw.split(";")
                for kw in kws:
                    if kw:
                        try:
                            associated.extend(input_rel["DATES"]["INVERSE"][q][relation][kw].keys())
                        except KeyError:
                            continue
    associated = set(associated)
    return len(associated)


def _initial_matrix(data):
    matrix = defaultdict(lambda: defaultdict(float))
    kws_all = set()
    # initialize "matrix" structure
    for kw, kw2, _, _, score in sorted(data):
        kws_all.add(kw)
        kws_all.add(kw2)
        score = round(score, 2)
        old_score = matrix[kw][kw2]
        inverse_old_score = matrix[kw2][kw]
        if score > old_score and score > inverse_old_score:
            matrix[kw][kw2] = score
            matrix[kw2][kw] = score
    return default_to_regular(matrix)


def _find_clusters(matrix, threshold, round_to=0):
    score_cond = 0
    clusters = set()
    # scores should be maximum, criterion used is cosine similarity
    # TODO: allow other criterions, with lower = better
    for kw, kw2_scores in matrix.items():
        for kw2, score in kw2_scores.items():
            if round_to:
                score = round(score, round_to)
            if not score > threshold or kw == kw2:
                continue
            # if not score_cond:
            #     score_cond = score
            if score == score_cond:
                clusters.add(tuple(sorted((kw, kw2))))
            elif score > score_cond:
                # elif score < score_cond:
                clusters = {tuple(sorted((kw, kw2)))}
                score_cond = score
    return sorted(clusters)


def process_clusters(data, threshold=0.3, input_rel=None, round_to=2):
    matrix = _initial_matrix(data)
    equivalents = []
    found_clusters = []
    # keep going until no clusters are found
    # also every good program needs to have a while True somewhere for maximum fun when something inevitably goes wrong
    while True:
        print(len(matrix))
        # 353
        clusters = _find_clusters(matrix, threshold, round_to=round_to)
        # end loop if no clusters are found
        if not clusters:
            break
        transitive = networkx_transitive(clusters)
        merged_clusters = _merge_same_level_clusters(clusters, transitive)
        # print(len(merged_clusters))
        # print("----")
        # print([x[0] for x in merged_clusters])
        found_clusters.append(merged_clusters)
        equivalents.extend(clusters)
        # prepare next_level of matrix by merging clusters together and erasing the columns / rows
        next_level = deepcopy(matrix)
        # get all clusters that are being merged in this iteration, so they can be pop()ped out of the dictionary
        to_remove = []
        for new_cluster, cluster_add in merged_clusters:
            # to_remove.append(old_cluster)
            # to_remove.append(cluster_add[0])
            # to_remove.append(cluster_add[1])
            to_remove.extend(cluster_add)
        to_remove = set(to_remove)
        # if len(merged_clusters) > len(to_remove):
        #     print("!!!!")
        for c in to_remove:
            next_level.pop(c, None)

        for new_cluster, cluster_elements in merged_clusters:
            for kw1, kw2_scores in matrix.items():
                # do not process "rows" that are being merged together
                if kw1 in to_remove:
                    continue
                distances = []
                # for each node in the new cluster
                for element in cluster_elements:
                    # pop out the "column" values
                    next_level[kw1].pop(element, None)
                    # find the distance that kw1 has to element
                    distance = matrix[kw1].get(element, 0.0)
                    if input_rel is not None:
                        distance *= num_associated(kw1, input_rel)
                        distance = round(distance, round_to)
                    distances.append(distance)
                # get the maximum distance (for klang higher is better) from kw1 to the new cluster
                distance = max(distances)
                # distance = min(distances)
                if distance == 0.0:
                    continue
                # set the distance of kw1 to the cluster as the maximum value
                next_level[kw1][new_cluster] = distance
                try:
                    # set the distance from the cluster to kw1
                    next_level[new_cluster][kw1] = distance
                except KeyError:
                    # this is raised only for the first kw1, kw2_scores loop iteration
                    next_level[new_cluster] = {kw1: distance}
        # set matrix to the next level and go into next iteration
        if len(next_level) > len(matrix):
            print(len(matrix), len(next_level))
            raise Exception("oh no")
        matrix = next_level
    if len(clusters) > 1:
        print("Found multiple clusters:\n", "\n".join(str(x) for x in clusters), "\n", "=" * 30)
    return equivalents, found_clusters


if __name__ == "__main__":
    # _p = "/home/madjura/PycharmProjects/klang/klang/SEMANTICS_scp_mini.p"
    _p = "/home/madjura/PycharmProjects/klang/klang/SEMANTICS_scp.p"
    # _p = "/home/madjura/PycharmProjects/klang/klang/SEMANTICS_imdb.p"
    with open(_p, "rb") as f:
        _data = dill.load(f)
    # good debug example, for imdb
    # cluster(_data[:200])
    _debug = [
        ("a", "b", 0, 0, 0.4),
        ("a", "d", 0, 0, 0.4),
        ("b", "a", 0, 0, 0.4),
        ("b", "c", 0, 0, 0.4),
        ("b", "d", 0, 0, 0.4),
        ("c", "b", 0, 0, 0.4),
        ("c", "d", 0, 0, 0.4),
        ("d", "a", 0, 0, 0.4),
        ("d", "b", 0, 0, 0.4),
        ("d", "c", 0, 0, 0.4)
    ]

    _debug2 = [
        ("a", "b", 0, 0, 0.4),
        # ("b", "c", 0, 0, 0.4),
        ("c", "d", 0, 0, 0.4),
        #  ("b", "f", 0, 0, 0.4)
    ]
    _, _found = process_clusters(_data, threshold=0)
