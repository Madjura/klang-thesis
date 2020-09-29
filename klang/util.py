from collections import defaultdict


def debut_keyword(keyword, input_rel, relation="hasKeyword", debuts_simple=None, direction="INVERSE", quantified=False,
                  swansong=False):
    if debuts_simple is None:
        debuts_simple = defaultdict(lambda: None)
    debut = debuts_simple[keyword]
    if debut is not None:
        return debut
    dates = []
    try:
        date_lists = input_rel["DATES"][direction][quantified][relation][keyword].values()
    except KeyError:
        return None
    for dl in date_lists:
        dates.extend(dl)
    dates = set(dates)
    if not dates:
        return None
    if type(list(dates)[0]) is tuple:
        dates = [x[0] for x in dates]
    try:
        if not swansong:
            debut = min(dates)
        else:
            debut = max(dates)
    except ValueError:
        return None
    debuts_simple[keyword] = debut
    return debut


def num_associated_keyword_all(keyword, input_rel):
    try:
        quantified = input_rel["DATES"]["INVERSE"][True].keys()
    except KeyError:
        # when no quantified relations exist
        quantified_num = 0
    else:
        quantified_num = sum(num_associated_keyword(keyword, input_rel, rel, quantified=True)[0] for rel in quantified)
    unquantified = input_rel["DATES"]["INVERSE"][False].keys()
    unquantified_num = sum(num_associated_keyword(keyword, input_rel, rel, quantified=False)[0] for rel in unquantified)
    return quantified_num + unquantified_num


def num_associated_keyword(keyword, input_rel, relation, quantified=False, keyword2=None):
    """
    Finds the number of associated elements for a given keyword.
    Optionally a second keyword can be passed, in which case the number of elements that are associated with BOTH
    keywords is returned.

    :param keyword: The keyword.
    :param input_rel: The input data.
    :param relation: The relation that is being considered.
    :param quantified: Optional. Default: False. Whether or not the relation is quantified.
    :param keyword2: Optional. The other keyword.
    :return: The number of associated elements with the keyword or the number of elmements associated with both keywords
        if a second keyword is passed.
    """
    if not quantified:
        try:
            elements = input_rel["DATES"]["INVERSE"][quantified][relation][keyword].keys()
        except KeyError:
            return 0, None
        if keyword2:
            try:
                elements2 = input_rel["DATES"]["INVERSE"][quantified][relation][keyword2].keys()
            except KeyError:
                return 0, None
            shared = set(elements).intersection(set(elements2))
            years = []
            for shared_element in shared:
                try:
                    years.extend(input_rel["DATES"]["REGULAR"][quantified][relation][shared_element][keyword])
                except KeyError:
                    continue
            return len(shared), years
        return len(elements), None
    else:
        # TODO: documentation for this part
        if keyword != keyword2:
            kw1_elem_vals = defaultdict(lambda: defaultdict(int))
            for kw1_elem, kw1_vals in input_rel["DATES"]["INVERSE"][quantified][relation][keyword].items():
                for kw1_val in kw1_vals:
                    elem, val = kw1_val
                    kw1_elem_vals[kw1_elem][elem] += val
            kw1_min = min(x for y in kw1_elem_vals.values() for x in y.values())
            kw1_elems = kw1_elem_vals.keys()

            if keyword2:
                kw2_elem_vals = defaultdict(lambda: defaultdict(int))
                for kw2_elem, kw2_vals in input_rel["DATES"]["INVERSE"][quantified][relation][keyword2].items():
                    for kw2_val in kw2_vals:
                        elem, val = kw2_val
                        kw2_elem_vals[kw2_elem][elem] += val
                kw2_elems = kw2_elem_vals.keys()
                kw2_min = min(x for y in kw2_elem_vals.values() for x in y.values())
            else:
                kw2_min = 0
                kw2_elems = []

            shared = set(kw1_elems).intersection(set(kw2_elems))
            years = []
            for shared_element in shared:
                shared_years = [x[0] for x in
                                input_rel["DATES"]["REGULAR"][quantified][relation][shared_element][keyword]]
                years.extend(shared_years)
            return kw1_min + kw2_min, years
            # return kw1_min + kw2_min, years
        else:
            kw1_values = input_rel["DATES"]["INVERSE"][quantified][relation][keyword].values()
            sum1 = sum(x[1] for y in kw1_values for x in y)  # keywords are identical, so only one calculation needed
            dates_kw = []
            relevant = input_rel["DATES"]["INVERSE"][quantified][relation][keyword]
            for _elem, dates in relevant.items():
                dates_kw.extend(x[0] for x in dates)
            return sum1 * 2, dates_kw


def find_supers(kw, input_rel):
    try:
        supers = list(input_rel["DATES"]["INVERSE"][False]["isSuper_True"].get(kw, []).keys())
    except KeyError:
        supers = []
    supers += list(input_rel["DATES"]["INVERSE"][False]["isSuper_False"].get(kw, []).keys())
    return supers


def get_equivalents(kw, input_rel, processed=None):
    # TODO: transitivity
    if processed is None:
        processed = {kw}
    else:
        processed.add(kw)
    equi = list(input_rel["DATES"]["REGULAR"][False]["relatedEquivalent"].get(kw, dict()).keys())
    equi += list(input_rel["DATES"]["INVERSE"][False]["relatedEquivalent"].get(kw, dict()).keys())
    equi = set(equi).difference(processed)
    out = set()
    if equi:
        for k in equi:
            if k not in processed:
                out.update(get_equivalents(k, input_rel, processed=processed))
    out.update(equi)
    return out


def get_relation_count(kw, input_rel):
    total = 0
    for q in [True, False]:
        try:
            relations = input_rel["DATES"]["REGULAR"][q].keys()
        except KeyError:
            continue  # happens if no qualified relations exist
        for r in relations:
            inverse = input_rel["DATES"]["INVERSE"][q][r].get(kw, list())
            regular = input_rel["DATES"]["REGULAR"][q][r].get(kw, list())
            total += len(inverse) + len(regular)
    return total
