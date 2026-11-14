import pytest
from pydantic import ValidationError

from app.questions import Cond, Path, QuerySpec, Question, Step, compile_path, explain_path


def test_uri_goes_through_parameters_not_the_query_text():
    uri = "http://kalnassag.com/onepiece#Straw_Hat_Pirates"
    p = Path(start="Character", steps=[Step(rel="AFFILIATES_WITH")], cond=Cond(kind="uri", uri=uri))
    true_q, known_q, params = compile_path(p)
    assert uri not in true_q and uri not in known_q and str(params["u"]) == uri
    assert "$u" in true_q
    for evil in ("http://x> } ; DROP ALL #", "x' OR 1=1 //"):                  # anything that could leave <...> is refused outright
        with pytest.raises(ValueError):
            compile_path(p.model_copy(update={"cond": Cond(kind="uri", uri=evil)}))


def test_identifier_injection_rejected():
    p = Path(start="Character", steps=[Step(rel='X" . } DROP ALL #')], cond=Cond(kind="exists"))
    with pytest.raises(ValueError):
        compile_path(p)


def test_only_known_start_categories_and_ops():
    with pytest.raises(ValidationError):
        Path(start="Person) DETACH DELETE (n", cond=Cond(kind="exists"))
    with pytest.raises(ValidationError):
        Cond(kind="cmp", prop="height", op="; DROP", value=1)


def test_cmp_scope_is_unknown_when_property_missing():
    p = Path(start="Character", cond=Cond(kind="cmp", prop="height", op=">=", value=180))
    true_q, known_q, _ = compile_path(p)
    assert "?e g:height ?val" in true_q and "FILTER(?val >= $v)" in true_q and "FILTER(" not in known_q and "g:height" in known_q


def test_open_scope_compiles_to_relationship_check(monkeypatch):
    p = Path(start="Character", steps=[Step(rel="OCCUPATION")], cond=Cond(kind="uri", uri="u"), scope="rel:OCCUPATION")
    assert "relType" not in compile_path(p)[1]                                  # closed world (default): every character is known
    monkeypatch.setattr("app.config.CLOSED_WORLD", False)
    assert 'g:relType "OCCUPATION"' in compile_path(p)[1]


def test_bad_scope_rejected():
    p = Path(start="Character", steps=[Step(rel="A")], cond=Cond(kind="uri", uri="u"), scope='rel:A" . } #')
    with pytest.raises(ValueError):
        compile_path(p)


def test_question_text_validation():
    spec = QuerySpec(paths=[Path(start="Ship", cond=Cond(kind="exists"))])
    with pytest.raises(ValidationError):
        Question(id="a", text="not a question", spec=spec)
    assert Question(id="a", text="Is it a ship?", spec=spec).text == "Is it a ship?"


def test_explanation_exists_only_with_a_path():
    assert explain_path(Path(start="Ship", cond=Cond(kind="exists")), "http://kalnassag.com/onepiece#X") is None


def test_status_scope_keeps_unknown_status_unknown():
    p = Path(start="Character", steps=[Step(rel="STATUS_OF_CHARACTER")], cond=Cond(kind="uri", uri="u"), scope="status")
    assert '"Alive", "Deceased"' in compile_path(p)[1]


def test_new_scopes_compile_and_validate(monkeypatch):
    monkeypatch.setattr("app.config.CLOSED_WORLD", False)
    from app.questions import validate_spec
    p = Path(start="DevilFruit", steps=[Step(rel="DEVIL_FRUIT_CURRENT_USER")], cond=Cond(kind="label", label="CaptainCharacter"), scope="last:rel:OCCUPATION")
    assert 'g:relType "OCCUPATION"' in compile_path(p)[1] and "?n1" in compile_path(p)[1]
    q = p.model_copy(update={"scope": "path"})
    assert "g:label" not in compile_path(q)[1]                                   # the path scope ignores the final condition
    assert validate_spec(QuerySpec(paths=[p]), {"DEVIL_FRUIT_CURRENT_USER", "OCCUPATION"}, {"CaptainCharacter"}) is None
    assert validate_spec(QuerySpec(paths=[p.model_copy(update={"scope": "last:rel:NOPE"})]), {"DEVIL_FRUIT_CURRENT_USER"}, {"CaptainCharacter"}) is not None
    with pytest.raises(ValueError):
        compile_path(p.model_copy(update={"scope": 'last:rel:X" . } #'}))
