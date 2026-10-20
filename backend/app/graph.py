import re
import time
from neo4j import GraphDatabase, Query

from . import config

_driver = None


def driver():
    global _driver
    if _driver is None:
        # A laptop that sleeps leaves half-dead TCP connections; without these limits a query can block for hours (seen in practice).
        _driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD), keep_alive=True,
                                       max_connection_lifetime=120, connection_timeout=10, connection_acquisition_timeout=30)
    return _driver


def run(query: str, **params):
    with driver().session() as s:
        return [r.data() for r in s.run(Query(query, timeout=60), **params)]


def wait_ready(timeout=120):
    end = time.time() + timeout
    while True:
        try:
            driver().verify_connectivity()
            return
        except Exception:
            if time.time() > end:
                raise
            time.sleep(2)


def local_name(uri: str) -> str:
    return uri.rsplit("#", 1)[-1] if "#" in uri else uri.rstrip("/").rsplit("/", 1)[-1]


def rel_type(pred_uri: str) -> str:
    """camelCase / PascalCase predicate -> UPPER_SNAKE Neo4j relationship type."""
    n = re.sub(r"[^0-9A-Za-z_]", "_", local_name(pred_uri))
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", n).upper()


def label_name(cls_uri: str) -> str:
    return re.sub(r"[^0-9A-Za-z_]", "_", local_name(cls_uri))
