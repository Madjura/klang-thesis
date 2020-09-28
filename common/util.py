from collections import defaultdict


def default_to_regular(d):
    # https://stackoverflow.com/a/26496899/5320601
    if isinstance(d, defaultdict) or isinstance(d, dict):
        d = {k: default_to_regular(v) for k, v in d.items()}
    return d


def scale2range(original_min, original_max, target_min, target_max, m):
    try:
        return (m - original_min) / (original_max - original_min) * (target_max - target_min) + target_min
    except ZeroDivisionError:
        return 0  # happens when there is only one feature
