import spacy


def _improve_segmentation(doc):
    """
    Helper function to improve spacy sentence segmentation specifically for product descriptions.
    A lot of descriptions contain lists that spacy does not properly handle. To fix that, this function marks every
    token that is followed by an empty token (i.e. newline) as the start of a sentence.
    This does NOT cause issues when there is a whitespace after a token even though it looks like it might.

    :param doc: The loaded spacy model.
    :return: The model, but with improved segmentation for sentence splitting.
    """
    for token in doc[:-1]:
        if not token.text.strip():
            # blank, such as \n \n etc.
            doc[token.i+1].is_sent_start = True
    return doc


def get_spacy_model(lang="en", for_descriptions=False):
    if lang == "de":
        # OLD: en_core_web_sm
        try:
            nlp = spacy.load("de_core_news_sm")
            print("--> Loaded spacy model de_core_news_sm")
        except OSError:
            print("--> Downloading spacy model de_core_news_sm")
            spacy.cli.download("de_core_news_sm")
            nlp = spacy.load("de_core_news_sm")
            print("--> Loaded spacy model de_core_news_sm")
    elif lang == "en":
        try:
            nlp = spacy.load("en_core_web_sm")
            print("--> Loaded spacy model en_core_web_sm")
        except OSError:
            print("--> Downloading spacy model en_core_web_sm")
            spacy.cli.download("en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")
            print("--> Loaded spacy model en_core_web_sm")
    else:
        # TODO: support for other languages
        # should work everywhere spacy models are loaded
        # currently not the case so loading not implemented yet
        raise Exception("Other languages not yet supported!")
    if for_descriptions:
        nlp.add_pipe(_improve_segmentation, before="parser")
    return nlp


def process_term(term, nouns_only=False):
    if term.like_url:
        term = "#URL#"
    elif term.like_num:
        term = "#NUM#"
    elif term.like_email:
        term = "#EMAIL#"
    elif term.text[0] == "#":
        term = "#HASHTAG#"
    elif term.text[0] == "@":
        term = "#MENTION#"
    elif term.is_stop:
        term = "#STOP#"
    elif term.is_punct:
        term = "#PUNCT#"
    else:
        if nouns_only and term.pos_ not in ["NOUN"]:
            term = f"#{term.pos_}#"
        else:
            # term = term.text.lower()
            term = term.lemma_.lower()
    return term
