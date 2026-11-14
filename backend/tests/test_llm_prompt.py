import re

from app import llm, questions

SCOPE_WORDS = {"closed", "status", "positive", "path"}


def _scope_examples():
    # every quoted scope token in the prompt, including the alternatives of the grammar line
    quoted = re.findall(r'"([^"\n]*)"', llm.SYSTEM)
    tokens = [t for q in quoted for t in q.split("|")]
    return {t for t in tokens if t in SCOPE_WORDS or t.startswith(("rel:", "prop:", "last:"))}


def test_scope_examples_match_scope_regex():
    examples = _scope_examples()
    assert {"closed", "positive", "status", "prop:haki_known", "last:prop:haki_known"} <= examples
    for scope in examples:
        assert questions.SCOPE.match(scope), scope


def test_prompt_no_longer_says_open_world():
    assert "open world" not in llm.SYSTEM.lower()
