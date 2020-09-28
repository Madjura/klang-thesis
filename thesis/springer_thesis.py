import pickle
from datetime import datetime

from common.util import default_to_regular
from klang.klangrelations import KlangRelationsFix


def create_klang_input_springer():
    with open("/media/madjura/BIG/PycharmProjects/scigraph-experiment/articles.p", "rb") as f:
        d = pickle.load(f)
    relations = KlangRelationsFix()
    for i, line in enumerate(d):
        print(f"Processing line {i+1} out of {len(d)}")
        url = line["url"]
        for a in line["about"]:
            try:
                kw = a["name"]
                relations.add_unquantified("hasKeyword", url, kw, int(line["sdDatePublished"].split("-")[0]))
            except KeyError:
                continue
    relations.relations = default_to_regular(relations.relations)
    with open("SPRINGER_EXPERIMENT.p", "wb") as f:
        pickle.dump(relations.relations, f)


if __name__ == "__main__":
    create_klang_input_springer()
