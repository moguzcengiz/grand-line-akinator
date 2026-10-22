"""Apache Jena Fuseki client: SPARQL queries over HTTP, Graph Store Protocol for loading.

The store holds the reasoned One Piece graph in named graphs (see ingestion.py):
  urn:akinator:explicit | curated | inferred   RDF edges + rdf:type triples; the graph a triple lives in IS its provenance
  urn:akinator:tbox                            schema + extension rules / constraints + curated facts: what implications.py reasons with
  urn:akinator:game                            per-node game data (g:name, g:category, g:label, g:popularity ...) and the
                                               relation name of every edge predicate (op:occupation g:relType "OCCUPATION")
The default graph is the union of the named graphs (tdb2:unionDefaultGraph), so plain queries see everything.
"""
import re
import time

import httpx
from rdflib import Literal, URIRef

from . import config

G = "http://kalnassag.com/akinator#"
GRAPHS = {p: f"urn:akinator:{p}" for p in ("explicit", "curated", "inferred", "game", "tbox")}
PREFIXES = f"PREFIX g: <{G}>\nPREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
_BAD_IRI = re.compile(r"[<>\"{}|^`\\\s]")
_PARAM = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_INT = {"integer", "int", "long", "short", "nonNegativeInteger", "positiveInteger"}
_FLOAT = {"decimal", "double", "float"}

_client = None


def client() -> httpx.Client:
    global _client
    if _client is None:
        # a laptop that sleeps leaves half-dead connections: bounded timeouts, never wait for hours
        _client = httpx.Client(base_url=config.FUSEKI_URL, timeout=httpx.Timeout(60, connect=10))
    return _client


def iri(u: str) -> URIRef:
    """A URI to substitute into a query; refuses anything that could break out of <...>."""
    if not u or _BAD_IRI.search(u):
        raise ValueError(f"bad IRI {u!r}")
    return URIRef(u)


def _term(v) -> str:
    if isinstance(v, URIRef):
        return f"<{iri(str(v))}>"
    if isinstance(v, (list, tuple, set)):
        return " ".join(_term(x) for x in v)
    if isinstance(v, bool):
        return "true" if v else "false"
    return Literal(v).n3()                                     # escapes quotes / newlines; ints and floats get their xsd datatype


def bind(query: str, **params) -> str:
    """Substitute $name placeholders: URIRef -> <iri>, str -> "literal", number -> typed literal, list -> space-separated terms (VALUES)."""
    return _PARAM.sub(lambda m: _term(params[m.group(1)]) if m.group(1) in params else m.group(0), query)


def _value(b: dict):
    if b["type"] == "uri":
        return b["value"]
    dt = b.get("datatype", "").rsplit("#", 1)[-1]
    if dt in _INT:
        return int(b["value"])
    if dt in _FLOAT:
        return float(b["value"])
    if dt == "boolean":
        return b["value"] == "true"
    return b["value"]


def run(query: str, **params) -> list[dict]:
    """SELECT -> list of {var: python value} (unbound -> None); ASK -> [{"ask": bool}]."""
    r = client().post(f"/{config.FUSEKI_DATASET}/sparql", data={"query": PREFIXES + bind(query, **params)},
                      headers={"Accept": "application/sparql-results+json"})
    r.raise_for_status()
    d = r.json()
    if "boolean" in d:
        return [{"ask": d["boolean"]}]
    names = d["head"]["vars"]
    return [{v: (_value(row[v]) if v in row else None) for v in names} for row in d["results"]["bindings"]]


def graph_of(name: str):
    """The triples of one named graph as an rdflib Graph."""
    from rdflib import Graph
    r = client().post(f"/{config.FUSEKI_DATASET}/sparql", data={"query": f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{GRAPHS[name]}> {{ ?s ?p ?o }} }}"},
                      headers={"Accept": "application/n-triples"})
    r.raise_for_status()
    return Graph().parse(data=r.text, format="nt")


def put_graph(name: str, ntriples: str):
    """Replace one named graph (Graph Store Protocol PUT, admin credentials)."""
    r = client().put(f"/{config.FUSEKI_DATASET}/data", params={"graph": GRAPHS[name]}, content=ntriples.encode(),
                     headers={"Content-Type": "application/n-triples"}, auth=(config.FUSEKI_USER, config.FUSEKI_PASSWORD), timeout=300)
    r.raise_for_status()


def ping():
    client().get("/$/ping").raise_for_status()


def wait_ready(timeout=120):
    end = time.time() + timeout
    while True:
        try:
            ping()
            return
        except Exception:
            if time.time() > end:
                raise
            time.sleep(2)


def local_name(uri: str) -> str:
    return uri.rsplit("#", 1)[-1] if "#" in uri else uri.rstrip("/").rsplit("/", 1)[-1]


def rel_type(pred_uri: str) -> str:
    """camelCase / PascalCase predicate -> UPPER_SNAKE relation name (the vocabulary of question specs)."""
    n = re.sub(r"[^0-9A-Za-z_]", "_", local_name(pred_uri))
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", n).upper()


def label_name(cls_uri: str) -> str:
    return re.sub(r"[^0-9A-Za-z_]", "_", local_name(cls_uri))
