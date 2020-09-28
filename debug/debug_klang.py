import json
from math import floor

from klang.util import debut_keyword


def _connected_by_relation(node, data, relation, direction="REGULAR"):
    return list(data["DATES"][direction][False][relation].get(node, {}).keys())


def generate_klang_graph(node, data):
    # node = "nxxxx"
    # for "normal" graph
    nodes = []
    edges = []

    # for timeline graph
    groups = ["isSuperAreaOf", "isSubAreaOf", "relatedEquivalent", "broaderThan", "contributesTo", "lessSpecificThan",
              "contributedToBy"]
    items = []

    # nodes that "node" is super of
    subs_nondate = _connected_by_relation(node, data, "isSuper_False")
    subs_date = _connected_by_relation(node, data, "isSuper_True")

    # nodes that "node" is a sub of
    supers_nondate = _connected_by_relation(node, data, "isSub_False")
    supers_date = _connected_by_relation(node, data, "isSub_True")

    equis1 = _connected_by_relation(node, data, "relatedEquivalent")
    # equis2 = set(_connected_by_relation(node, data, "relatedEquivalent", direction="INVERSE"))

    broader = _connected_by_relation(node, data, "broaderGeneric")
    less_broad = _connected_by_relation(node, data, "broaderGeneric", direction="INVERSE")

    contributes = _connected_by_relation(node, data, "contributesTo")
    contributed_to_by = _connected_by_relation(node, data, "contributesTo", direction="INVERSE")

    node_debut = debut_keyword(node, data)
    if node_debut is None:
        node_debut = 0
    debuts = [node_debut]
    kw2debut = {node: node_debut}
    print("CALCULATING DEBUTS")
    for kw in subs_nondate + subs_date + supers_nondate + supers_date + broader + less_broad + contributed_to_by:
        debut = debut_keyword(kw, data)
        if debut is None:
            debut = 0
        kw2debut[kw] = debut
        debuts.append(debut)
    debuts = sorted(set(debuts))
    year_first = int(min(debuts))
    year_last = int(max(debuts))
    month_first = round((min(debuts) % 1 + 1 / 12) * 12)
    month_last = round((max(debuts) % 1 + 1 / 12) * 12)
    intervals = 12 * (year_last - year_first) - (12 - month_first) + month_last
    if intervals == 0:
        intervals = 1

    interval_step = ((max(debuts) - min(debuts)) or 1) / intervals

    print("PROCESSING SUPERS")
    supers_all = set(supers_date + supers_nondate)
    added = set()
    for s in supers_all:
        debut_kw = debut_keyword(s, data)
        swansong_kw = debut_keyword(s, data, swansong=True)
        interval_pos = int((debut_kw - min(debuts)) / interval_step)
        if s not in added:
            nodes.append({"id": s, "label": s, "level": interval_pos, "group": interval_pos})
        edges.append(
            {"from": s, "to": node, "color": {"color": "red"}, "smooth": {"type": "curvedCCW", "roundness": 0.1}})
        added.add(s)
        date = False
        nondate = False
        if s in supers_date:
            date = True
        if s in supers_nondate:
            nondate = True
        kw_date_year = floor(debut_kw)
        kw_date_month = int(((debut_kw % 1) + 1 / 12) * 12)
        if kw_date_month < 10:
            kw_date_month = "0" + str(kw_date_month)

        swansong_date_year = floor(swansong_kw)
        swansong_date_month = int(((swansong_kw % 1) + 1 / 12) * 12)
        if swansong_date_month < 10:
            swansong_date_month = "0" + str(swansong_date_month)
        desc = ""
        if date:
            desc += "date"
        if nondate and date:
            desc += ", nondate"
        elif nondate:
            desc += "nondate"
        items.append({"id": s + "_SUPER", "group": "isSuperAreaOf", "start": f"{kw_date_month}/{kw_date_year}",
                      "content": f"{s} ({desc})", "end": f"{swansong_date_month}/{swansong_date_year}"})

    subs_all = set(subs_date + subs_nondate)
    for s in subs_all:
        debut_kw = debut_keyword(s, data)
        swansong_kw = debut_keyword(s, data, swansong=True)
        interval_pos = int((debut_kw - min(debuts)) / interval_step)
        if s not in added:
            nodes.append({"id": s, "label": s, "level": interval_pos, "group": interval_pos})
        edges.append(
            {"from": s, "to": node, "color": {"color": "navy"}, "smooth": {"type": "curvedCCW", "roundness": 0.15}})
        added.add(s)
        date = False
        nondate = False
        if s in subs_date:
            date = True
        if s in subs_nondate:
            nondate = True
        kw_date_year = floor(debut_kw)
        kw_date_month = int(((debut_kw % 1) + 1 / 12) * 12)
        if kw_date_month < 10:
            kw_date_month = "0" + str(kw_date_month)

        swansong_date_year = floor(swansong_kw)
        swansong_date_month = int(((swansong_kw % 1) + 1 / 12) * 12)
        if swansong_date_month < 10:
            swansong_date_month = "0" + str(swansong_date_month)
        desc = ""
        if date:
            desc += "date"
        if nondate and date:
            desc += ", nondate"
        elif nondate:
            desc += "nondate"
        items.append({"id": s + "_SUB", "group": "isSubAreaOf", "start": f"{kw_date_month}/{kw_date_year}",
                      "content": f"{s} ({desc})", "end": f"{swansong_date_month}/{swansong_date_year}"})

    for s in equis1:
        debut_kw = debut_keyword(s, data)
        swansong_kw = debut_keyword(s, data, swansong=True)
        # interval_pos = int((debut_kw - min(debuts)) / interval_step)
        # nodes.append({"id": s + "_EQUIS", "label": s, "level": interval_pos})
        kw_date_year = floor(debut_kw)
        kw_date_month = int(((debut_kw % 1) + 1 / 12) * 12)
        if kw_date_month < 10:
            kw_date_month = "0" + str(kw_date_month)

        swansong_date_year = floor(swansong_kw)
        swansong_date_month = int(((swansong_kw % 1) + 1 / 12) * 12)
        if swansong_date_month < 10:
            swansong_date_month = "0" + str(swansong_date_month)
        items.append({"id": s + "_EQUI", "group": "relatedEquivalent", "start": f"{kw_date_month}/{kw_date_year}",
                      "content": s, "end": f"{swansong_date_month}/{swansong_date_year}"})

    for s in contributes:
        debut_kw = debut_keyword(s, data)
        swansong_kw = debut_keyword(s, data, swansong=True)
        interval_pos = int((debut_kw - min(debuts)) / interval_step)
        if s not in added:
            nodes.append({"id": s, "label": s, "level": interval_pos, "group": interval_pos})
        edges.append(
            {"from": s, "to": node, "color": {"color": "gold"}, "smooth": {"type": "curvedCCW", "roundness": 0.2}})
        added.add(s)
        kw_date_year = floor(debut_kw)
        kw_date_month = int(((debut_kw % 1) + 1 / 12) * 12)
        if kw_date_month < 10:
            kw_date_month = "0" + str(kw_date_month)

        swansong_date_year = floor(swansong_kw)
        swansong_date_month = int(((swansong_kw % 1) + 1 / 12) * 12)
        if swansong_date_month < 10:
            swansong_date_month = "0" + str(swansong_date_month)
        items.append({"id": s + "_CONTRIBUTES", "group": "contributesTo", "start": f"{kw_date_month}/{kw_date_year}",
                      "content": s, "end": f"{swansong_date_month}/{swansong_date_year}"})

    for s in contributed_to_by:
        debut_kw = debut_keyword(s, data)
        swansong_kw = debut_keyword(s, data, swansong=True)
        # interval_pos = int((debut_kw - min(debuts)) / interval_step)
        # if s not in added:
        #     nodes.append({"id": s, "label": s, "level": interval_pos, "group": interval_pos})
        # edges.append(
        #     {"from": s, "to": node, "color": {"color": "gold"}, "smooth": {"type": "curvedCCW", "roundness": 0.2}})
        # added.add(s)
        kw_date_year = floor(debut_kw)
        kw_date_month = int(((debut_kw % 1) + 1 / 12) * 12)
        if kw_date_month < 10:
            kw_date_month = "0" + str(kw_date_month)

        swansong_date_year = floor(swansong_kw)
        swansong_date_month = int(((swansong_kw % 1) + 1 / 12) * 12)
        if swansong_date_month < 10:
            swansong_date_month = "0" + str(swansong_date_month)
        items.append(
            {"id": s + "_CONTRIBUTED_TO_BY", "group": "contributedToBy", "start": f"{kw_date_month}/{kw_date_year}",
             "content": s, "end": f"{swansong_date_month}/{swansong_date_year}"})

    for s in broader:
        debut_kw = debut_keyword(s, data)
        swansong_kw = debut_keyword(s, data, swansong=True)
        # interval_pos = int((debut_kw - min(debuts)) / interval_step)
        # if s not in added:
        #     nodes.append({"id": s, "label": s, "level": interval_pos, "group": interval_pos})
        # edges.append({"from": s, "to": node, "color": {"color": "gold"}, "smooth": {"type": "curvedCCW", "roundness": 0.2}})
        # added.add(s)
        kw_date_year = floor(debut_kw)
        kw_date_month = int(((debut_kw % 1) + 1 / 12) * 12)
        if kw_date_month < 10:
            kw_date_month = "0" + str(kw_date_month)

        swansong_date_year = floor(swansong_kw)
        swansong_date_month = int(((swansong_kw % 1) + 1 / 12) * 12)
        if swansong_date_month < 10:
            swansong_date_month = "0" + str(swansong_date_month)
        items.append(
            {"id": s + "_BROADER", "group": "broaderThan", "start": f"{kw_date_month}/{kw_date_year}", "content": s,
             "end": f"{swansong_date_month}/{swansong_date_year}"})

    for s in less_broad:
        debut_kw = debut_keyword(s, data)
        swansong_kw = debut_keyword(s, data, swansong=True)
        # interval_pos = int((debut_kw - min(debuts)) / interval_step)
        # if s not in added:
        #     nodes.append({"id": s, "label": s, "level": interval_pos, "group": interval_pos})
        # edges.append({"from": s, "to": node, "color": {"color": "gold"}, "smooth": {"type": "curvedCCW", "roundness": 0.2}})
        # added.add(s)
        kw_date_year = floor(debut_kw)
        kw_date_month = int(((debut_kw % 1) + 1 / 12) * 12)
        if kw_date_month < 10:
            kw_date_month = "0" + str(kw_date_month)

        swansong_date_year = floor(swansong_kw)
        swansong_date_month = int(((swansong_kw % 1) + 1 / 12) * 12)
        if swansong_date_month < 10:
            swansong_date_month = "0" + str(swansong_date_month)
        items.append(
            {"id": s + "_LESSBROAD", "group": "lessSpecificThan", "start": f"{kw_date_month}/{kw_date_year}",
             "content": s, "end": f"{swansong_date_month}/{swansong_date_year}"})

    interval_pos = int((node_debut - min(debuts)) / interval_step)
    nodes.append({"id": node, "label": node, "level": interval_pos, "group": interval_pos})

    return json.dumps(nodes), json.dumps(edges), json.dumps(groups), json.dumps(items)
