"""C16 S3-E development evaluation (never reads the retrieval oracle, its fixture, the SYN site or the holdout).

Corpus: the synthetic dev passages (dev/dev_set.json) + a seeded sample of real passages as distractors (HybridBench
`dump`, 3,000, seed 16). Queries: the dev set (semantic / lexical / out-of-domain) and the 43 C14 walkthrough queries
(unlabelled; used only for gate firing rates at real-passage scale).

  python -I dev_eval.py embed <model> <repr>            embed corpus + queries (cached under E:\\Mimamsa-Data\\c16s3e\\vec)
  python -I dev_eval.py eval <model> <repr> <out.json>  every fusion / admission rule below, all metrics

Resource bounds (shared host): half the logical CPUs for ONNX Runtime, process priority below normal, batch 8.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEV = HERE.parent / "dev" / "dev_set.json"
WALK = HERE.parents[1] / "c15_hybrid" / "scripts" / "queries.json"
DATA = Path(r"E:\Mimamsa-Data\c16s3e")
DISTRACTORS = DATA / "dev" / "distractors_3000_seed16.jsonl"
MODELS = Path(r"E:\Mimamsa-Data\models")
THREADS = max(1, (os.cpu_count() or 2) // 2)

# model name -> (dir, onnx file, pooling, query prefix, passage prefix)
SPECS = {
    "e5-small": ("multilingual-e5-small/614241f622f53c4eeff9890bdc4f31cfecc418b3", "onnx/model.onnx", "onnx/tokenizer.json", "mean", "query: ", "passage: "),
    "e5-base": ("multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a", "onnx/model.onnx", "onnx/tokenizer.json", "mean", "query: ", "passage: "),
    "e5-large": ("multilingual-e5-large/3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3", "onnx/model_qint8_avx512_vnni.onnx", "onnx/tokenizer.json", "mean", "query: ", "passage: "),
    "bge-m3": ("bge-m3/4de13258303883538bd53b696b452bf8099f0858", "onnx/model_int8.onnx", "tokenizer.json", "cls", "", ""),
    "arctic-m2": ("snowflake-arctic-embed-m-v2.0/95c2741480856aa9666782eb4afe11959938017f", "onnx/model_int8.onnx", "tokenizer.json", "cls", "query: ", ""),
}


def below_normal():
    try:
        import psutil
        p = psutil.Process()
        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 10)
    except Exception as e:  # noqa: BLE001
        print("priority not lowered:", e, file=sys.stderr)


def resolve(name):
    d, onnx, tok, pool, qp, pp = SPECS[name]
    base = MODELS / d.split("/")[0]
    rev = d.split("/")[1]
    if rev == "REV":
        revs = [x for x in base.iterdir() if x.is_dir()]
        assert len(revs) == 1, revs
        root = revs[0]
    else:
        root = base / rev
    return root, root / onnx, root / tok, pool, qp, pp


class Embedder:
    def __init__(self, name):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.root, onnx, tok, self.pool, self.qp, self.pp = resolve(name)
        so = ort.SessionOptions()
        so.intra_op_num_threads = THREADS
        so.inter_op_num_threads = 1
        self.s = ort.InferenceSession(str(onnx), so, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.s.get_inputs()}
        self.int8 = "int8" in onnx.name
        self.tok = Tokenizer.from_file(str(tok))
        self.tok.no_padding()
        self.tok.no_truncation()

    def ids(self, text, max_tokens):
        text = re.sub(r"\s+", " ", text).strip()
        e = self.tok.encode(text)
        ids = e.ids
        if len(ids) > max_tokens:   # keep <s> ... </s>
            ids = ids[: max_tokens - 1] + [ids[-1]]
        return ids

    def embed(self, texts, max_tokens, batch=8):
        # Dynamically quantised (int8) ONNX models compute activation scales per call, so padding in a batch changes
        # every vector in it (measured: cosine 0.96-0.99 between batched and single for arctic-embed int8). They are
        # embedded one text per call, which makes each vector a function of its own text only (as at query time).
        if self.int8:
            batch = 1
        out = []
        for s in range(0, len(texts), batch):
            enc = [self.ids(t, max_tokens) for t in texts[s:s + batch]]
            n = max(len(e) for e in enc)
            pad = self.tok.token_to_id("<pad>")
            pad = 1 if pad is None else pad
            ids = np.full((len(enc), n), pad, dtype=np.int64)
            mask = np.zeros((len(enc), n), dtype=np.int64)
            for i, e in enumerate(enc):
                ids[i, :len(e)] = e
                mask[i, :len(e)] = 1
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(ids)
            h = self.s.run(None, feed)[0]
            if h.ndim == 2:
                v = h
            elif self.pool == "cls":
                v = h[:, 0, :]
            else:
                m = mask[:, :, None].astype(np.float32)
                v = (h * m).sum(1) / m.sum(1)
            v = v / np.linalg.norm(v, axis=1, keepdims=True)
            out.append(v.astype(np.float32))
        return np.concatenate(out)


def load_corpus():
    dev = json.loads(DEV.read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in DISTRACTORS.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Every STRIDE-th row (still a uniform sample): stride 3 = 1,000 distractors, used for the large models on the
    # contended host. All models are compared at the same stride.
    rows = rows[::int(os.environ.get("C16_DISTRACTOR_STRIDE", "1"))]
    corpus = [{"id": p["id"], "title": p["title"], "doc_type": p["doc_type"], "text": p["text"], "dev": True} for p in dev["passages"]]
    corpus += [{"id": f"R{r['i']}", "title": r.get("title") or "", "doc_type": r.get("doc_type") or "", "text": r["text"], "dev": False} for r in rows]
    walk = json.loads(WALK.read_text(encoding="utf-8"))
    return dev, corpus, walk


# ---------------------------------------------------------------- passage representations
WINDOW_TOKENS, WINDOW_STRIDE = 128, 64


def representations(corpus, repr_name, emb: Embedder | None):
    """Returns (texts, owner) where owner[k] = corpus index of text k (several texts per passage for windows)."""
    texts, owner = [], []
    for i, p in enumerate(corpus):
        if repr_name == "plain":
            texts.append(p["text"]); owner.append(i)
        elif repr_name == "title":
            texts.append(f"{p['title']}. {p['text']}" if p["title"] else p["text"]); owner.append(i)
        elif repr_name == "window":
            words = p["text"].split()
            # word windows approximating 128 tokens (about 90 words), stride half a window; short passages: one window
            w, st = 90, 45
            if len(words) <= w:
                texts.append(p["text"]); owner.append(i)
            else:
                for s in range(0, len(words), st):
                    texts.append(" ".join(words[s:s + w])); owner.append(i)
                    if s + w >= len(words):
                        break
        else:
            raise SystemExit(f"unknown representation {repr_name}")
    return texts, owner


def cache_path(model, repr_name, texts, kind):
    h = hashlib.sha256(("\u0001".join(texts)).encode("utf-8")).hexdigest()[:16]
    p = DATA / "vec" / model / repr_name
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{kind}-{h}.npy"


class TextCache:
    """Per-text vector cache for one model (sha256 of the exact model input -> vector), so strides and runs reuse work."""
    def __init__(self, model):
        self.dir = DATA / "vec" / model
        self.dir.mkdir(parents=True, exist_ok=True)
        self.keys_f, self.vec_f = self.dir / "textcache.keys.json", self.dir / "textcache.npy"
        self.keys = json.loads(self.keys_f.read_text()) if self.keys_f.exists() else []
        self.vec = np.load(self.vec_f) if self.vec_f.exists() else None
        self.pos = {k: i for i, k in enumerate(self.keys)}

    @staticmethod
    def key(t):
        return hashlib.sha256(t.encode("utf-8")).hexdigest()

    def add(self, texts, vs):
        for t in texts:
            self.pos[self.key(t)] = len(self.keys)
            self.keys.append(self.key(t))
        self.vec = vs if self.vec is None else np.concatenate([self.vec, vs])
        np.save(self.vec_f, self.vec)
        self.keys_f.write_text(json.dumps(self.keys))

    def get(self, texts):
        return np.stack([self.vec[self.pos[self.key(t)]] for t in texts])

    def missing(self, texts):
        seen, out = set(), []
        for t in texts:
            k = self.key(t)
            if k not in self.pos and k not in seen:
                seen.add(k); out.append(t)
        return out


def get_vectors(model, repr_name, corpus, queries, emb=None, compute=False):
    texts, owner = representations(corpus, repr_name, emb)
    if True:
        tc = TextCache(model)
        _, _, _, _, qpre, ppre = resolve(model)
        ptexts, qtexts = [ppre + x for x in texts], [qpre + q for q in queries]
        miss_p, miss_q = tc.missing(ptexts), tc.missing(qtexts)
        if (miss_p or miss_q) and not compute:
            raise SystemExit(f"vectors missing for {model}/{repr_name}; run embed first")
        if miss_q:
            emb = emb or Embedder(model)
            tc.add(miss_q, emb.embed(miss_q, 128))
        if miss_p:
            emb = emb or Embedder(model)
            t = time.time()
            for s in range(0, len(miss_p), 128):
                chunk = miss_p[s:s + 128]
                tc.add(chunk, emb.embed(chunk, 256))
                print(f"  {model}/{repr_name}: {s + len(chunk)}/{len(miss_p)} ({time.time() - t:.0f} s)", file=sys.stderr, flush=True)
            print(f"  embedded {len(miss_p)} texts in {time.time() - t:.0f} s", file=sys.stderr)
        return tc.get(ptexts), np.array(owner), tc.get(qtexts)
    pp = cache_path(model, repr_name, texts, "passages")
    qtexts = [q for q in queries]
    qp = cache_path(model, "queries", qtexts, "queries")
    need = (not pp.exists()) or (not qp.exists())
    if need and not compute:
        raise SystemExit(f"vectors missing for {model}/{repr_name}; run embed first")
    if need:
        emb = emb or Embedder(model)
        if not qp.exists():
            np.save(qp, emb.embed([emb.qp + q for q in qtexts], 128))
        if not pp.exists():
            t = time.time()
            ptexts = [emb.pp + x for x in texts]
            vs = []
            for s in range(0, len(ptexts), 256):
                vs.append(emb.embed(ptexts[s:s + 256], 256))
                print(f"  {model}/{repr_name}: {s + len(vs[-1])}/{len(ptexts)} ({time.time() - t:.0f} s)", file=sys.stderr, flush=True)
            np.save(pp, np.concatenate(vs))
            print(f"  embedded {len(ptexts)} texts in {time.time() - t:.0f} s", file=sys.stderr)
    return np.load(pp), np.array(owner), np.load(qp)


# ---------------------------------------------------------------- lexical (BM25 approximation of the service)
STOP = set("a an the of to in on for and or is are was were be been by with from at as it its this that these those i me my we our you your he him his she her they them their do does did can could will would shall should may might must not no any all what which who whom when where why how than then there here into over under about after before during while if so such only also just".split())


def toks(t):
    return [w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in STOP]


def stem(w):
    return w[:5]


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.tf = []
        self.df = {}
        for d in docs:
            c = {}
            for w in toks(d):
                c[w] = c.get(w, 0) + 1
            self.tf.append(c)
            for w in c:
                self.df[w] = self.df.get(w, 0) + 1
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.len) / len(self.len)
        self.N = len(docs)

    def rank(self, q):
        qs = set(toks(q))
        sc = {}
        for w in qs:
            df = self.df.get(w)
            if not df:
                continue
            idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
            for i, c in enumerate(self.tf):
                f = c.get(w)
                if f:
                    sc[i] = sc.get(i, 0) + idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
        return [i for i, _ in sorted(sc.items(), key=lambda x: (-x[1], x[0]))]


# ---------------------------------------------------------------- admission and fusion rules
def dense_scores(P, owner, qv, n):
    s = P @ qv
    best = np.full(n, -1.0, dtype=np.float32)
    np.maximum.at(best, owner, s)    # max over a passage's windows
    return best


def rrf(lex, dense, k=60, lex_depth=200):
    acc = {}
    for i, p in enumerate(lex[:lex_depth]):
        acc[p] = acc.get(p, 0) + 1 / (k + i + 1)
    for i, p in enumerate(dense):
        acc[p] = acc.get(p, 0) + 1 / (k + i + 1)
    return [p for p, _ in sorted(acc.items(), key=lambda x: (-x[1], x[0]))]


def admitted(rule, s, bg):
    """Dense passages admitted for one query (best first) under an admission rule.
    s: cosine of every corpus passage; bg: (mu, sd) of the query's cosines over the shipped background sample."""
    order = np.argsort(-s, kind="stable")
    kind = rule["kind"]
    if kind == "floor":
        return [int(i) for i in order[:100] if s[i] >= rule["floor"]]
    if kind == "gate_rank":      # the floor gates the query; admission is by rank (top K) once the gate is open
        return [int(i) for i in order[:rule["k"]]] if s[order[0]] >= rule["floor"] else []
    if kind == "z":              # per-query normalisation against the background distribution
        mu, sd = bg
        return [int(i) for i in order[:100] if (s[i] - mu) / sd >= rule["z"]]
    if kind == "gate_z_rank":    # z gate on the best passage, then top K
        mu, sd = bg
        return [int(i) for i in order[:rule["k"]]] if (s[order[0]] - mu) / sd >= rule["z"] else []
    raise ValueError(kind)


def evaluate(model, repr_name, out):
    dev, corpus, walk = load_corpus()
    qtexts = [q["text"] for q in dev["queries"]] + [q["query"] for q in walk]
    P, owner, Q = get_vectors(model, repr_name, corpus, qtexts)
    n = len(corpus)
    idx = {p["id"]: i for i, p in enumerate(corpus)}
    bm = BM25([p["text"] for p in corpus])
    # Background: the real distractor passages only (what a vector pack could ship), plain representation scores.
    real = np.array([not p["dev"] for p in corpus])
    S = np.stack([dense_scores(P, owner, Q[j], n) for j in range(len(qtexts))])
    bgs = [(float(S[j][real].mean()), float(S[j][real].std())) for j in range(len(qtexts))]
    # C14 floor rule recomputed for this model/representation: median over walkthrough queries of p99.9 over real passages
    nw = len(walk)
    p999 = sorted(float(np.quantile(S[len(dev["queries"]) + j][real], 0.999)) for j in range(nw))
    floor = p999[nw // 2]
    # z rule: median over walkthrough queries of the z of their p99.9 passage (the same statistic in z units)
    zs = sorted((float(np.quantile(S[len(dev["queries"]) + j][real], 0.999)) - bgs[len(dev["queries"]) + j][0]) / bgs[len(dev["queries"]) + j][1] for j in range(nw))
    zfloor = zs[nw // 2]
    rules = {
        "floor_c14": {"kind": "floor", "floor": floor},
        "gate_rank10": {"kind": "gate_rank", "floor": floor, "k": 10},
        "gate_rank20": {"kind": "gate_rank", "floor": floor, "k": 20},
        "z_c14": {"kind": "z", "z": zfloor},
        "gate_z_rank10": {"kind": "gate_z_rank", "z": zfloor, "k": 10},
        "nofloor": {"kind": "floor", "floor": -1.0},
    }
    res = {"model": model, "repr": repr_name, "corpus": n, "real": int(real.sum()), "floor_c14": round(floor, 4), "z_c14": round(zfloor, 3), "rules": {}}
    per_query_dense = {}
    for j, q in enumerate(dev["queries"]):
        s = S[j]
        order = np.argsort(-s, kind="stable")
        rank = {int(p): r + 1 for r, p in enumerate(order)}
        per_query_dense[q["id"]] = {"kind": q["kind"], "best": round(float(s[order[0]]), 4), "mu": round(bgs[j][0], 4), "sd": round(bgs[j][1], 4),
                                    "relevant": {r: {"dense_rank": rank[idx[r]], "cos": round(float(s[idx[r]]), 4),
                                                     "z": round((float(s[idx[r]]) - bgs[j][0]) / bgs[j][1], 2)} for r in q["relevant"]}}
    res["dense"] = per_query_dense
    for name, rule in rules.items():
        r = {"semantic_at10": 0, "semantic_n": 0, "semantic_gate_open": 0, "lexical_top3": 0, "lexical_n": 0, "lexical_gate_open": 0,
             "ood_gate_open": 0, "ood_n": 0, "walk_gate_open": 0, "walk_n": nw, "walk_mean_admitted": 0.0, "fails": []}
        for j, q in enumerate(dev["queries"]):
            adm = admitted(rule, S[j], bgs[j])
            lex = bm.rank(q["text"])
            fused = rrf(lex, adm) if adm else lex
            top10 = fused[:10]
            rel = [idx[x] for x in q["relevant"]]
            if q["kind"] == "semantic":
                r["semantic_n"] += 1
                r["semantic_gate_open"] += bool(adm)
                ok = all(x in top10 for x in rel)
                r["semantic_at10"] += ok
                if not ok:
                    r["fails"].append(q["id"])
            elif q["kind"] == "lexical":
                r["lexical_n"] += 1
                r["lexical_gate_open"] += bool(adm)
                r["lexical_top3"] += all(x in fused[:3] for x in rel)
            else:
                r["ood_n"] += 1
                r["ood_gate_open"] += bool(adm)
        tot = 0
        for j in range(nw):
            adm = admitted(rule, S[len(dev["queries"]) + j], bgs[len(dev["queries"]) + j])
            r["walk_gate_open"] += bool(adm)
            tot += len(adm)
        r["walk_mean_admitted"] = round(tot / nw, 1)
        res["rules"][name] = r | {"rule": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rule.items()}}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"{model}/{repr_name}: floor {floor:.4f} z {zfloor:.2f}")
    for name, r in res["rules"].items():
        print(f"  {name:14} sem@10 {r['semantic_at10']}/{r['semantic_n']} (gate {r['semantic_gate_open']})  lex top3 {r['lexical_top3']}/{r['lexical_n']} (gate {r['lexical_gate_open']})"
              f"  ood gate {r['ood_gate_open']}/{r['ood_n']}  walk gate {r['walk_gate_open']}/{nw} adm {r['walk_mean_admitted']}  fails {r['fails']}")


def overlap_check():
    dev = json.loads(DEV.read_text(encoding="utf-8"))
    ps = {p["id"]: p for p in dev["passages"]}
    for q in dev["queries"]:
        if q["kind"] != "semantic":
            continue
        qs = {stem(w) for w in toks(q["text"])}
        for r in q["relevant"]:
            common = qs & {stem(w) for w in toks(ps[r]["text"])}
            print(q["id"], r, "shared stems:", sorted(common) or "none")


def main():
    below_normal()
    cmd = sys.argv[1]
    if cmd == "overlap":
        return overlap_check()
    model, repr_name = sys.argv[2], sys.argv[3]
    if cmd == "embed":
        dev, corpus, walk = load_corpus()
        qtexts = [q["text"] for q in dev["queries"]] + [q["query"] for q in walk]
        t = time.time()
        get_vectors(model, repr_name, corpus, qtexts, compute=True)
        print(f"{model}/{repr_name} ready in {time.time() - t:.0f} s")
    elif cmd == "eval":
        evaluate(model, repr_name, sys.argv[4])


if __name__ == "__main__":
    main()
