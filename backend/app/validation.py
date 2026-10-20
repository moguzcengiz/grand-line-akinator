"""SHACL validation (pyshacl). OWL RL infers; SHACL checks that the data satisfies the intended constraints."""
from rdflib import Graph, Namespace, RDF
from pyshacl import validate

from . import config

SH = Namespace("http://www.w3.org/ns/shacl#")


def shacl_report(data: Graph, limit: int = 10) -> dict:
    shapes = Graph().parse(str(config.ROOT / "ontology/shapes.ttl"), format="turtle")
    _, results, _ = validate(data, shacl_graph=shapes, inference="none", abort_on_first=False)
    rows, viol, warn = [], 0, 0
    for r in results.subjects(RDF.type, SH.ValidationResult):
        sev = results.value(r, SH.resultSeverity)
        is_warn = sev == SH.Warning
        warn, viol = warn + is_warn, viol + (not is_warn)
        if len(rows) < limit and not is_warn:
            rows.append({"focus": str(results.value(r, SH.focusNode)).rsplit("#", 1)[-1], "path": str(results.value(r, SH.resultPath)).rsplit("#", 1)[-1],
                         "message": str(results.value(r, SH.resultMessage))})
    return {"violations": viol, "warnings": warn, "examples": rows}
