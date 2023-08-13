from spacy.language import Language
from spacy.tokens import Doc
from medcat.config import Config
from medcat.pipeline.pipe_runner import PipeRunner
from pythainlp.util import isthai


def tag_skip_and_punct(nlp: Language, name: str, config: Config) -> "_Tagger":
    """Detects and tags spacy tokens that are punctuation and that should be skipped.

    Args:
        nlp (spacy.language.<lng>):
            The base spacy NLP pipeline.
        name (str):
            The component instance name.
        config (medcat.config.Config):
            Global config for medcat.

    Returns:
        _Tagger: The tagger
    """
    return _Tagger(nlp, name, config)

def tag_skip_punct_lang(nlp: Language, name: str, config: Config) -> "_Modified_Tagger":
    """Detects and tags spacy tokens that are punctuation and that should be skipped.
    and language tag: token._.lang = 'th' (Thai) and token._.lang = 'en' (English)

    Args:
        nlp (spacy.language.<lng>):
            The base spacy NLP pipeline.
        name (str):
            The component instance name.
        config (medcat.config.Config):
            Global config for medcat.

    Returns:
        _Modified_Tagger: The tagger
    """
    return _Modified_Tagger(nlp, name, config)


# This is not elegant.
tag_skip_and_punct.name = "tag_skip_and_punct"  # type: ignore
tag_skip_punct_lang.name = "tag_skip_punct_lang"  # type: ignore

class _Tagger(PipeRunner):

    # Override
    def __init__(self, nlp: Language, name: str, config: Config) -> None:
        self.name = name
        self.config = config
        super().__init__(self.config.general['workers'])

    # Override
    def __call__(self, doc: Doc) -> Doc:
        # Make life easier
        cnf_p = self.config.preprocessing

        for token in doc:
            if self.config.punct_checker.match(token.lower_) and token.text not in cnf_p['keep_punct']:
                # There can't be punct in a token if it also has text
                token._.is_punct = True
                token._.to_skip = True
            elif self.config.word_skipper.match(token.lower_):
                # Skip if specific strings
                token._.to_skip = True
            elif cnf_p['skip_stopwords'] and token.is_stop:
                token._.to_skip = True

        return doc

class _Modified_Tagger(PipeRunner):

    # Override
    def __init__(self, nlp: Language, name: str, config: Config) -> None:
        self.name = name
        self.config = config
        super().__init__(self.config.general['workers'])

    # Override
    def __call__(self, doc: Doc) -> Doc:
        # Make life easier
        cnf_p = self.config.preprocessing

        for token in doc:
            if self.config.punct_checker.match(token.lower_) and token.text not in cnf_p['keep_punct']:
                # There can't be punct in a token if it also has text
                token._.is_punct = True
                token._.to_skip = True
            elif self.config.word_skipper.match(token.lower_):
                # Skip if specific strings
                token._.to_skip = True
            elif cnf_p['skip_stopwords'] and token.is_stop:
                token._.to_skip = True
            elif isthai(token.text, ignore_chars="+-.,"):
                token._.lang = 'th'
            else:
                token._.lang = 'en'

        return doc
