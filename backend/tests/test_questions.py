import pytest
from pydantic import ValidationError

from app.questions import Cond, Path, QuerySpec, Question, Step, compile_path, compile_explain


def test_uri_goes_through_parameters_not_the_query_text():
    evil = "x' OR 1=1 //"
    p = Path(start="Character", steps=[Step(rel="AFFILIATES_WITH")], cond=Cond(kind="uri", uri=evil))
    true_q, known_q, params = compile_path(p)
    assert evil not in true_q and evil not in known_q and params["u"] == evil
    assert "$u" in true_q


def test_identifier_injection_rejected():
    p = Path(start="Character", steps=[Step(rel="X`]-() DETACH DELETE n //")], cond=Cond(kind="exists"))
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
    assert "e.height >= $v" in true_q and "IS NOT NULL" in known_q


def test_open_scope_compiles_to_relationship_check():
    p = Path(start="Character", steps=[Step(rel="OCCUPATION")], cond=Cond(kind="uri", uri="u"), scope="rel:OCCUPATION")
    assert "`OCCUPATION`" in compile_path(p)[1]


def test_bad_scope_rejected():
    p = Path(start="Character", steps=[Step(rel="A")], cond=Cond(kind="uri", uri="u"), scope="rel:A`) //")
    with pytest.raises(ValueError):
        compile_path(p)


def test_question_text_validation():
    spec = QuerySpec(paths=[Path(start="Ship", cond=Cond(kind="exists"))])
    with pytest.raises(ValidationError):
        Question(id="a", text="not a question", spec=spec)
    assert Question(id="a", text="Is it a ship?", spec=spec).text == "Is it a ship?"


def test_explain_query_exists_only_with_a_path():
    assert compile_explain(Path(start="Ship", cond=Cond(kind="exists"))) is None
    assert "$e" in compile_explain(Path(start="Ship", steps=[Step(rel="OPERATED_BY")], cond=Cond(kind="exists")))


def test_status_scope_keeps_unknown_status_unknown():
    p = Path(start="Character", steps=[Step(rel="STATUS_OF_CHARACTER")], cond=Cond(kind="uri", uri="u"), scope="status")
    assert "'Alive','Deceased'" in compile_path(p)[1]


def test_new_scopes_compile_and_validate():
    from app.questions import validate_spec
    p = Path(start="DevilFruit", steps=[Step(rel="DEVIL_FRUIT_CURRENT_USER")], cond=Cond(kind="label", label="CaptainCharacter"), scope="last:rel:OCCUPATION")
    assert "`OCCUPATION`" in compile_path(p)[1] and "n1" in compile_path(p)[1]
    q = p.model_copy(update={"scope": "path"})
    assert "WHERE" not in compile_path(q)[1].split("EXISTS")[1].split("RETURN")[0]
    assert validate_spec(QuerySpec(paths=[p]), {"DEVIL_FRUIT_CURRENT_USER", "OCCUPATION"}, {"CaptainCharacter"}) is None
    assert validate_spec(QuerySpec(paths=[p.model_copy(update={"scope": "last:rel:NOPE"})]), {"DEVIL_FRUIT_CURRENT_USER"}, {"CaptainCharacter"}) is not None
    with pytest.raises(ValueError):
        compile_path(p.model_copy(update={"scope": "last:rel:X`) //"}))
