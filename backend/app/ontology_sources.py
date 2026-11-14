"""Polite, persistent official-profile index for ontology research.

The source cache is advisory evidence, never an automatic RDF writer. Fetches are
restricted to the official ONE PIECE site, obey its robots.txt when published,
and are spaced by a configurable minimum interval (default: one request/second).
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import threading
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from rdflib import Graph, Literal, RDF, RDFS, SKOS, URIRef

from . import config
from .perf import record as metric

ROOT = config.ROOT
CACHE = ROOT / "work/source-cache/one-piece.com"
DIRECTORY = ROOT / "work/source-cache/official-profile-index.json"
METRICS = ROOT / "work/research/performance.jsonl"
HOST = "one-piece.com"
BOT = "OntologyResearchBot/1.0 (polite source cache)"
PROFILE_RE = re.compile(r"^/character/([^/]+)/index\.html$", re.I)
SKIP_SLUGS = {"index", "syllabary", "birthday"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean_url(url):
    p = urlparse(url)
    if p.scheme not in ("http", "https") or p.hostname not in {HOST, "www." + HOST}:
        raise ValueError(f"URL outside allowed official host: {url}")
    path = p.path or "/"
    return urlunparse(("https", HOST, path, "", p.query, ""))


class TextIndex(HTMLParser):
    """Collect anchor labels and page text without executing scripts."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.title, self.h1, self.text = [], [], [], []
        self._anchor = None
        self._title = self._h1 = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self._anchor = [a["href"], []]
        if tag == "title": self._title = True
        if tag == "h1": self._h1 = True

    def handle_endtag(self, tag):
        if tag == "a" and self._anchor is not None:
            href, words = self._anchor
            self.links.append((href, " ".join(words).strip()))
            self._anchor = None
        if tag == "title": self._title = False
        if tag == "h1": self._h1 = False

    def handle_data(self, data):
        s = " ".join(data.split())
        if not s: return
        self.text.append(s)
        if self._anchor is not None: self._anchor[1].append(s)
        if self._title: self.title.append(s)
        if self._h1: self.h1.append(s)


def _robots_allowed(url):
    """404 means no published robots file; other failures fail closed."""
    from urllib.robotparser import RobotFileParser
    robots = "https://one-piece.com/robots.txt"
    req = Request(robots, headers={"User-Agent": BOT})
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=20) as r:
            body = r.read(256_000).decode("utf-8", "replace")
        rp = RobotFileParser(robots)
        rp.parse(body.splitlines())
        allowed = rp.can_fetch(BOT, url)
        metric("robots_policy_fetch", time.perf_counter() - started, status=200, allowed=allowed)
        return allowed, "published"
    except HTTPError as e:
        if e.code == 404:
            metric("robots_policy_fetch", time.perf_counter() - started, status=404, allowed=True)
            return True, "robots_404_no_published_rules"
        metric("robots_policy_fetch", time.perf_counter() - started, status=e.code, allowed=False)
        return False, f"robots_http_{e.code}"
    except (URLError, TimeoutError, OSError) as e:
        metric("robots_policy_fetch", time.perf_counter() - started, status="unavailable", allowed=False)
        return False, f"robots_unavailable:{type(e).__name__}"


class Fetcher:
    def __init__(self, delay=1.0):
        self.delay = max(1.0, float(delay))
        self.last_request_start = 0.0
        self.cooldown_until = 0.0
        self.robots_allowed_cache = {}
        self._robots_lock = threading.Lock()
        self._start_lock = threading.Lock()

    def fetch(self, raw_url):
        url = clean_url(raw_url)
        key = hashlib.sha256(url.encode()).hexdigest()
        body_path, meta_path = CACHE / f"{key}.html", CACHE / f"{key}.json"
        if body_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            metric("source_cache_hit", 0, url=url, bytes=body_path.stat().st_size)
            return url, body_path.read_bytes(), meta | {"cache_hit": True}
        origin = urlparse(url).netloc
        with self._robots_lock:
            if origin not in self.robots_allowed_cache:
                self.robots_allowed_cache[origin] = _robots_allowed(url)
        allowed, robots_state = self.robots_allowed_cache[origin]
        if not allowed: raise PermissionError(f"robots policy prevents fetching: {robots_state}")
        with self._start_lock:
            now_mono = time.monotonic()
            wait = max(self.delay - (now_mono - self.last_request_start), self.cooldown_until - now_mono)
            if wait > 0: time.sleep(wait)
            self.last_request_start = time.monotonic()
        started = time.perf_counter()
        req = Request(url, headers={"User-Agent": BOT, "Accept": "text/html"})
        try:
            with urlopen(req, timeout=25) as r:
                status, content_type = r.status, r.headers.get("content-type", "")
                body = r.read(2_000_001)
                headers = {k.lower(): r.headers.get(k) for k in ("etag", "last-modified", "cache-control")}
        except HTTPError as e:
            status, content_type, body = e.code, "", e.read(512_000)
            retry_after = e.headers.get("Retry-After") if e.headers else None
            headers = {k.lower(): (e.headers.get(k) if e.headers else None)
                       for k in ("etag", "last-modified", "cache-control", "retry-after")}
            if status in (429, 503):
                try: cooldown = max(self.delay, float(retry_after)) if retry_after else 60.0
                except ValueError: cooldown = 60.0
                with self._start_lock:
                    self.cooldown_until = max(self.cooldown_until, time.monotonic() + cooldown)
                metric("source_rate_limit_backoff", cooldown, url=url, status=status, retry_after=retry_after)
        elapsed = time.perf_counter() - started
        allowed_type = any(kind in content_type.lower() for kind in ("html", "xml"))
        if status != 200 or not allowed_type:
            metric("source_fetch_rejected", elapsed, url=url, status=status, content_type=content_type)
            raise RuntimeError(f"source fetch rejected: HTTP {status}, {content_type}")
        if len(body) > 2_000_000: raise RuntimeError("source exceeds 2 MB cache limit")
        CACHE.mkdir(parents=True, exist_ok=True)
        body_path.write_bytes(body)
        meta = {"url": url, "fetched_at": now(), "http_status": status, "content_type": content_type,
                "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "fetch_seconds": round(elapsed, 6),
                "robots_policy": robots_state, "response_headers": headers, "cache_hit": False}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        metric("source_fetch", elapsed, url=url, status=status, bytes=len(body), robots=robots_state)
        return url, body, meta


def parse_html(body):
    p = TextIndex()
    p.feed(body.decode("utf-8", "replace"))
    return p


def discover_directory(delay=1.0, max_pages=100):
    """Read the official XML sitemap and persist direct character profile URLs."""
    start = time.perf_counter()
    fetcher = Fetcher(delay)
    url, body, _ = fetcher.fetch("https://one-piece.com/sitemap.xml")
    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", body.decode("utf-8", "replace"), re.I)
    profiles = {}
    for loc in locs:
        try: absolute = clean_url(loc)
        except ValueError: continue
        m = PROFILE_RE.match(urlparse(absolute).path)
        if m and m.group(1).casefold() not in SKIP_SLUGS:
            profiles[absolute] = {"url": absolute, "slug": m.group(1), "directory_label": None}
    data = {"generated_at": now(), "host": HOST, "robots_file": "https://one-piece.com/robots.txt",
            "robots_result": "404 (no published rules found during crawl)", "sitemap_url": url,
            "directory_pages": [url],
            "profile_count": len(profiles), "profiles": sorted(profiles.values(), key=lambda r: r["url"])}
    DIRECTORY.parent.mkdir(parents=True, exist_ok=True)
    DIRECTORY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metric("source_directory_index", time.perf_counter() - start, pages=1, profiles=len(profiles), sitemap_bytes=len(body))
    return data


FIELD_MAP = {
    "通称": ("alias", "http://www.w3.org/2004/02/skos/core#altLabel"),
    "組織": ("affiliation", str(URIRef(config.OP + "affiliatesWith"))),
    "悪魔の実": ("devil_fruit", str(URIRef(config.OP + "hasDevilFruit"))),
    "懸賞金": ("bounty", str(URIRef(config.OP + "hasBounty"))),
    "船": ("ship", str(URIRef(config.OPX + "operatedBy"))),
    "所属船": ("ship", str(URIRef(config.OPX + "ownsShip"))),
    "種族": ("species", str(URIRef(config.OP + "race"))),
    "覇気": ("haki", str(URIRef(config.OPX + "hasHaki"))),
    "肩書き": ("rank_or_role", str(URIRef(config.OP + "occupation"))),
    "役職": ("rank_or_role", str(URIRef(config.OP + "occupation"))),
    "階級": ("rank_or_role", str(URIRef(config.OP + "occupation"))),
}


class ProfileFacts(HTMLParser):
    """Extract primary profile fields and exclude definition lists in related-character cards."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.card_flags, self.current_dl, self.current_dt, self.current_dd = [], [], None, None, None
        self.profile_depth = None
        self.profile_mode = None
        self.card_depth = 0
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        in_related_card = self.card_depth > 0
        is_card = tag == "div" and "el-card-block" in classes
        if is_card:
            self.card_depth += 1
        modern = (tag == "div" and attrs.get("data-column") == "profile"
                  and self.profile_mode is None and not in_related_card and not is_card)
        legacy = (tag == "div" and "el-list-term" in classes and attrs.get("data-txt-row") == "horizontal"
                  and self.profile_mode is None and not in_related_card and not is_card)
        if modern:
            self.profile_mode = "modern"
            self.profile_depth = len(self.stack)
        elif legacy:
            self.profile_mode = "legacy"
            self.profile_depth = len(self.stack)
        self.stack.append(tag)
        self.card_flags.append(is_card)
        if tag == "dl" and self.profile_depth is not None: self.current_dl = {"dt": [], "dd": []}
        elif tag == "dt" and self.current_dl is not None: self.current_dt = []
        elif tag == "dd" and self.current_dl is not None: self.current_dd = []
        elif tag == "br" and self.current_dd is not None: self.current_dd.append("\n")

    def handle_endtag(self, tag):
        if tag == "dt" and self.current_dt is not None:
            self.current_dl["dt"] = self.current_dt
            self.current_dt = None
        elif tag == "dd" and self.current_dd is not None:
            self.current_dl["dd"] = self.current_dd
            self.current_dd = None
        elif tag == "dl" and self.current_dl is not None:
            label = " ".join(" ".join(self.current_dl["dt"]).split())
            value = "\n".join(" ".join(x.split()) for x in "".join(self.current_dl["dd"]).split("\n") if x.strip())
            if label and value: self.rows.append((label, value))
            self.current_dl = None
        if self.stack: self.stack.pop()
        was_card = self.card_flags.pop() if self.card_flags else False
        if tag == "div" and self.profile_depth is not None and len(self.stack) == self.profile_depth:
            self.profile_depth = None
        if was_card:
            self.card_depth = max(0, self.card_depth - 1)

    def handle_data(self, data):
        s = " ".join(data.split())
        if not s or self.current_dl is None: return
        if self.current_dt is not None: self.current_dt.append(s)
        elif self.current_dd is not None: self.current_dd.append(s)


class ProfileHeader(HTMLParser):
    """Capture the short role/organization line under the primary character title."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.header_depth = None
        self.current_p = None
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if tag == "div" and "el-heading-lv1__container" in classes and self.header_depth is None:
            self.header_depth = len(self.stack)
        if tag == "p" and self.header_depth is not None and self.current_p is None:
            self.current_p = []
        elif tag == "br" and self.current_p is not None:
            self.current_p.append("\n")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "p" and self.current_p is not None:
            value = " ".join("".join(self.current_p).split())
            if value: self.paragraphs.append(value)
            self.current_p = None
        if self.stack: self.stack.pop()
        if tag == "div" and self.header_depth is not None and len(self.stack) == self.header_depth:
            self.header_depth = None

    def handle_data(self, data):
        if self.current_p is not None:
            self.current_p.append(data)


def graph_name_index(graph, characters_only=False):
    rows = []
    characters = set(graph.subjects(RDF.type, URIRef(config.OP + "Character"))) if characters_only else None
    for entity, pred, label in graph:
        if characters is not None and entity not in characters: continue
        if pred in {RDFS.label, SKOS.prefLabel, SKOS.altLabel, SKOS.hiddenLabel} and isinstance(label, Literal):
            rows.append((str(label), entity))
    entities = characters if characters is not None else set(graph.subjects(RDF.type, None))
    for entity in entities:
        rows.append((str(entity).rsplit("#", 1)[-1].replace("_", " "), entity))
    index = {}
    for label, entity in rows:
        index.setdefault(normalize(label), set()).add(entity)
    return index


def match_directory(graph, index_data, priority_map=None):
    """Conservative exact normalized slug/name matching; collisions stay in review queue."""
    names = graph_name_index(graph, characters_only=True)
    exact, review, unmatched = [], [], []
    for profile in index_data.get("profiles", []):
        slug = profile["slug"].replace("_", " ")
        normalized_slug = normalize(slug)
        candidates = sorted(names.get(normalized_slug, set()))
        if len(candidates) == 1:
            uri = URIRef(candidates[0])
            exact.append({"entity_uri": str(candidates[0]), "profile_url": profile["url"], "slug": profile["slug"],
                          "confidence": 0.98, "match_basis": "unique exact normalized canonical name, alias, Japanese name, or identifier",
                          "queue_priority": (priority_map or {}).get(str(candidates[0]), 0),
                          "types": sorted(str(t).rsplit("#", 1)[-1] for t in graph.objects(uri, RDF.type)),
                          "existing_affiliations": sorted(str(x).rsplit("#", 1)[-1] for x in graph.objects(uri, URIRef(config.OP + "affiliatesWith")))})
        elif len(candidates) > 1:
            review.append({"profile_url": profile["url"], "slug": profile["slug"], "candidate_entity_uris": candidates,
                           "candidate_context": [{"entity_uri": uri,
                             "types": sorted(str(t).rsplit("#", 1)[-1] for t in graph.objects(URIRef(uri), RDF.type)),
                             "existing_affiliations": sorted(str(x).rsplit("#", 1)[-1] for x in graph.objects(URIRef(uri), URIRef(config.OP + "affiliatesWith")))}
                             for uri in candidates],
                           "confidence": 0.0, "status": "ambiguous_identity_review"})
        else:
            # Keep compound identifiers such as "Saint_<entity key>" visible
            # for contextual review; never promote a substring to an exact match.
            embedded = set()
            for label, entities in names.items():
                if len(label) >= 5 and (label in normalized_slug or normalized_slug in label):
                    embedded.update(entities)
            if embedded:
                candidates = sorted(embedded)
                review.append({"profile_url": profile["url"], "slug": profile["slug"],
                               "candidate_entity_uris": candidates,
                               "candidate_context": [{"entity_uri": uri,
                                 "types": sorted(str(t).rsplit("#", 1)[-1] for t in graph.objects(URIRef(uri), RDF.type)),
                                 "existing_affiliations": sorted(str(x).rsplit("#", 1)[-1] for x in graph.objects(URIRef(uri), URIRef(config.OP + "affiliatesWith")))}
                                 for uri in candidates],
                               "confidence": 0.0, "status": "embedded_identifier_review"})
            else:
                unmatched.append({"profile_url": profile["url"], "slug": profile["slug"], "status": "no_exact_name_match"})
    exact.sort(key=lambda x: (-x["queue_priority"], x["entity_uri"]))
    return {"generated_at": now(), "profile_count": len(index_data.get("profiles", [])),
            "exact_match_count": len(exact), "ambiguous_count": len(review), "unmatched_count": len(unmatched),
            "matches": exact, "review_queue": review, "unmatched": unmatched}


def normalize(s): return re.sub(r"[^\w]", "", str(s).casefold(), flags=re.UNICODE)


def _extract_profile_document(canonical_url, body, meta, index, value_index):
    started = time.perf_counter()
    parsed = parse_html(body)
    fact_parser = ProfileFacts()
    fact_parser.feed(body.decode("utf-8", "replace"))
    header_parser = ProfileHeader()
    header_parser.feed(body.decode("utf-8", "replace"))
    metric("source_html_parse", time.perf_counter() - started, url=canonical_url, bytes=len(body))
    started = time.perf_counter()
    slug = urlparse(canonical_url).path.split("/")[-2]
    normalized_slug = normalize(slug.replace("_", " "))
    slug_hits = index.get(normalized_slug, set())
    title_name = " ".join(parsed.h1).strip()
    normalized_title = normalize(title_name)
    title_hits = index.get(normalized_title, set())
    identity_conflict = bool(slug_hits and title_hits and not (slug_hits & title_hits))
    exact_hits = (slug_hits & title_hits) if slug_hits and title_hits else (slug_hits or title_hits)
    # Compound official slugs/titles often add honorifics or explanatory names.
    # Preserve unique embedded identifier/name matches for human review, but do
    # not treat them as exact identity matches or attach their facts to an entity.
    embedded_hits = set()
    if not exact_hits and not identity_conflict:
        for label, entities in index.items():
            if len(label) < 3:
                continue
            if (label in normalized_slug or label in normalized_title
                    or normalized_slug in label or normalized_title in label):
                embedded_hits.update(entities)
    hits = (slug_hits | title_hits) if identity_conflict else (exact_hits or embedded_hits)
    exact = len(exact_hits) == 1 and not identity_conflict
    entity = next(iter(hits)) if exact else None
    facts = []
    seen_fields = set()
    for label, value in fact_parser.rows:
        mapped = FIELD_MAP.get(label)
        if not mapped or label in seen_fields: continue
        seen_fields.add(label)
        field, predicate = mapped
        values = value.split("\n") if field in {"affiliation", "devil_fruit", "haki", "rank_or_role", "ship"} else [value]
        for source_value in values:
            source_value = source_value.strip()
            if not source_value: continue
            object_hits = sorted(value_index.get(normalize(source_value), set()))
            if field == "alias":
                object_value = {"kind": "literal", "value": source_value, "language": "ja"}
            else:
                object_value = ({"kind": "uri", "value": str(object_hits[0])} if len(object_hits) == 1
                                else {"kind": "unresolved_source_text", "value": source_value})
            status = "candidate_requires_semantic_review"
            confidence = 0.98 if exact and len(object_hits) == 1 else 0.85 if exact else 0.0
            if not exact: status = "identity_review_required"
            elif field == "alias": status = "candidate_requires_duplicate_review"
            elif field == "bounty": status = "not_directly_mappable_without_bounty_record_identity"
            elif field in {"affiliation", "devil_fruit", "species", "haki", "rank_or_role", "ship"} and len(object_hits) != 1:
                status = "value_match_review_required"
            facts.append({"entity_uri": str(entity) if entity else None, "entity_match": "exact" if exact else "ambiguous_or_unmatched",
                          "match_candidates": sorted(str(x) for x in (hits or title_hits or slug_hits)),
                          "predicate": predicate, "object_or_literal": object_value, "source_url": canonical_url,
                          "evidence": {"section_label": label, "exact_text": source_value, "page_title": title_name,
                                       "document_sha256": meta["sha256"]}, "confidence": confidence,
                          "temporal_qualifier": None, "extraction_status": status, "field": field})
    source_fields = ([{"label": "キャラクター名", "exact_text": title_name, "source_url": canonical_url,
                       "document_sha256": meta["sha256"]}] if title_name else [])
    source_fields.extend({"label": label, "exact_text": value, "source_url": canonical_url,
                          "document_sha256": meta["sha256"]} for label, value in fact_parser.rows)
    source_fields.extend({"label": "プロフィール見出し", "exact_text": value, "source_url": canonical_url,
                          "document_sha256": meta["sha256"]} for value in header_parser.paragraphs)
    metric("source_fact_extraction_and_match", time.perf_counter() - started, url=canonical_url,
           facts=len(facts), exact_match=bool(exact), cache_hit=meta.get("cache_hit"))
    return {"url": canonical_url, "document_sha256": meta["sha256"], "title": title_name,
            "entity_uri": str(entity) if entity else None, "match_status": "exact" if exact else "review_required",
            "candidate_entity_uris": sorted(str(x) for x in (hits or title_hits or slug_hits)), "facts": facts,
            "source_fields": source_fields,
            "fetch": meta}


def extract_profile(url, graph, index=None, delay=1.0, fetcher=None, value_index=None):
    started = time.perf_counter()
    index = index or graph_name_index(graph, characters_only=True)
    value_index = value_index or graph_name_index(graph)
    fetcher = fetcher or Fetcher(delay)
    canonical_url, body, meta = fetcher.fetch(url)
    result = _extract_profile_document(canonical_url, body, meta, index, value_index)
    metric("source_extract_and_match", time.perf_counter() - started, url=canonical_url,
           facts=len(result["facts"]), cache_hit=meta.get("cache_hit"))
    return result


def extract_profiles(urls, graph, delay=1.0, workers=4, parse_workers=1):
    """Fetch with bounded concurrency under a global start-rate limit; parse separately."""
    fetcher = Fetcher(delay)
    index_started = time.perf_counter()
    index, value_index = graph_name_index(graph, characters_only=True), graph_name_index(graph)
    metric("source_match_indexes", time.perf_counter() - index_started,
           character_name_keys=len(index), ontology_name_keys=len(value_index))
    started = time.perf_counter()
    documents, failures = [None] * len(urls), []
    worker_count = max(1, min(8, int(workers)))
    with ThreadPoolExecutor(max_workers=worker_count) as fetch_pool:
        futures = {fetch_pool.submit(fetcher.fetch, url): (i, url) for i, url in enumerate(urls)}
        for n, future in enumerate(as_completed(futures), 1):
            i, url = futures[future]
            try: documents[i] = future.result()
            except Exception as error:
                failures.append({"url": url, "match_status": "fetch_failed", "facts": [],
                                 "extraction_status": type(error).__name__})
            if n % 25 == 0:
                print(f"source fetch progress: {n}/{len(urls)} urls; {len(failures)} failures", flush=True)
    documents = [x for x in documents if x is not None]
    tasks = [(canonical_url, body, meta, index, value_index) for canonical_url, body, meta in documents]
    parse_worker_count = max(1, min(8, int(parse_workers)))
    with ThreadPoolExecutor(max_workers=parse_worker_count) as pool:
        results = list(pool.map(lambda args: _extract_profile_document(*args), tasks))
    results.extend(failures)
    metric("source_batch_extract", time.perf_counter() - started, documents=len(urls),
           facts=sum(len(x["facts"]) for x in results), exact_matches=sum(x["match_status"] == "exact" for x in results),
           workers=worker_count, fetch_workers=worker_count, parse_workers=parse_worker_count,
           fetch_failures=len(failures))
    return results


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("directory"); d.add_argument("--delay", type=float, default=1.0); d.add_argument("--max-pages", type=int, default=100)
    m = sub.add_parser("match"); m.add_argument("--out", default="work/source-cache/ontology-profile-matches.json")
    e = sub.add_parser("extract"); e.add_argument("url"); e.add_argument("--out", default="work/source-cache/extracted-facts.json")
    b = sub.add_parser("extract-batch"); b.add_argument("urls_json"); b.add_argument("--out", default="work/source-cache/extracted-batch-facts.json"); b.add_argument("--workers", type=int, default=4); b.add_argument("--parse-workers", type=int, default=1); b.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()
    if args.cmd == "directory":
        data = discover_directory(args.delay, args.max_pages)
        print(json.dumps({"directory_pages": len(data["directory_pages"]), "profile_count": data["profile_count"], "path": str(DIRECTORY)}))
    elif args.cmd == "match":
        from .ontology import load_sources
        base, ext = load_sources()
        data = json.loads(DIRECTORY.read_text(encoding="utf-8"))
        started = time.perf_counter()
        queue_path = ROOT / "work/ontology-research-queue.jsonl"
        priorities = {}
        if queue_path.exists():
            for line in queue_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    priorities[row["entity_uri"]] = row.get("priority", 0)
        result = match_directory(base + ext, data, priorities)
        metric("source_identity_match", time.perf_counter() - started,
               profiles=result["profile_count"], exact=result["exact_match_count"],
               ambiguous=result["ambiguous_count"], unmatched=result["unmatched_count"])
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: result[k] for k in ("profile_count", "exact_match_count", "ambiguous_count", "unmatched_count")} | {"path": str(out)}))
    elif args.cmd == "extract-batch":
        from .ontology import load_sources
        base, ext = load_sources()
        urls = json.loads((ROOT / args.urls_json).read_text(encoding="utf-8"))
        results = extract_profiles(urls, base + ext, delay=args.delay, workers=args.workers, parse_workers=args.parse_workers)
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"documents": len(results), "exact_matches": sum(x["match_status"] == "exact" for x in results),
                          "facts": sum(len(x["facts"]) for x in results), "path": str(out)}))
    else:
        from .ontology import load_sources
        base, ext = load_sources()
        result = extract_profile(args.url, base + ext)
        path = ROOT / args.out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"match_status": result["match_status"], "facts": len(result["facts"]), "path": str(path)}))


if __name__ == "__main__": main()
