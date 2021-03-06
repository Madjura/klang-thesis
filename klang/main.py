import pickle
import sys
import time

import dill

from klang.klang_algorithm import init_klang


#########################################
# CAN BE FOUND IN "klang_inputs_raw.zip"#
#########################################
def load_imdb_data():
    with open("../klang_inputs_raw/klang_imdb_input.p", "rb") as f:
        data = pickle.load(f)
    return data


def spike_titaness():
    with open("../klang_inputs_raw/klang_spike_week_input.p", "rb") as f:
        data = dill.load(f)
    return data


def spike_titaness_month():
    with open("../klang_inputs_raw/klang_spike_month_input.p", "rb") as f:
        data = dill.load(f)
    return data


if __name__ == "__main__":
    _data = load_imdb_data();
    _out_name = "IMDB-TESTESTEST"
    _data = spike_titaness_month()

    # ADJUST PATHS
    SCORES_PATH = "/home/madjura/PycharmProjects/klang/klang/scores"
    RELATIONS_PATH = "/home/madjura/PycharmProjects/klang/klang/relations"
    # keywords_all = list(_data["DATES"]["INVERSE"][False]["hasKeyword"].keys())
    # WITH STORES: 2069.332406282425
    # 1869.9188256263733
    s = time.time()
    init_klang(_data, _out_name, shared_percentile=50, all_keywords=True, shared_percentile_ambi=95)
    print(time.time() - s)
