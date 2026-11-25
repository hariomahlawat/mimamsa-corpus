"""Embed corpus chunks and queries with one ONNX model on CPU; record throughput, latency and memory.

python -I embed.py <model_key> <models_dir> <chunks.jsonl> <queries.json> <out_dir> [--threads 4] [--max-len 256]
Outputs: <out_dir>/<key>.chunks.npy, <key>.queries.npy, <key>.ids.json, <key>.perf.json
"""
import argparse, json, os, sys, time, resource
from pathlib import Path
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from models import MODELS


def rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024
    return None


class Encoder:
    def __init__(self, key, models_dir, threads=4, max_len=256, onnx_override=None):
        repo, onnx_path, pooling, qp, pp, dim = MODELS[key]
        onnx_path = onnx_override or onnx_path
        d = Path(models_dir) / key
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess = ort.InferenceSession(str(d / onnx_path), so, providers=["CPUExecutionProvider"])
        self.tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        self.tok.enable_truncation(max_len)
        self.tok.enable_padding(pad_id=self.tok.token_to_id("[PAD]") or 0)
        self.inputs = {i.name for i in self.sess.get_inputs()}
        self.pooling, self.qp, self.pp, self.dim = pooling, qp, pp, dim

    def encode(self, texts, batch=32, prefix=""):
        out = []
        for i in range(0, len(texts), batch):
            enc = self.tok.encode_batch([prefix + t for t in texts[i:i + batch]])
            ids = np.array([e.ids for e in enc], dtype=np.int64)
            mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(ids)
            h = self.sess.run(None, feed)[0]
            if h.ndim == 2:      # already pooled
                v = h
            elif self.pooling == "cls":
                v = h[:, 0]
            else:
                m = mask[..., None].astype(np.float32)
                v = (h * m).sum(1) / np.clip(m.sum(1), 1e-9, None)
            v = v / np.linalg.norm(v, axis=1, keepdims=True)
            out.append(v.astype(np.float32))
        return np.vstack(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key"); ap.add_argument("models_dir"); ap.add_argument("chunks"); ap.add_argument("queries")
    ap.add_argument("out"); ap.add_argument("--threads", type=int, default=4); ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--int8", action="store_true", help="dynamic int8 quantised copy made locally with onnxruntime.quantization")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rss0 = rss_mb(); t0 = time.perf_counter()
    override = None
    if a.int8:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        src = Path(a.models_dir) / a.key / MODELS[a.key][1]
        dst = src.with_name("model_int8_local.onnx")
        if not dst.exists():
            quantize_dynamic(str(src), str(dst), weight_type=QuantType.QInt8)
        override = str(dst.relative_to(Path(a.models_dir) / a.key))
    name = a.key + ("-int8" if a.int8 else "") + a.tag
    enc = Encoder(a.key, a.models_dir, a.threads, a.max_len, override)
    load_s = time.perf_counter() - t0; rss_loaded = rss_mb()
    chunks = [json.loads(l) for l in open(a.chunks)]
    queries = json.load(open(a.queries))
    # query latency (single query, batch 1) after 3 warm-ups
    qtexts = [q["query"] for q in queries]
    for t in qtexts[:3]: enc.encode([t], 1, enc.qp)
    lat = []
    for t in qtexts:
        s = time.perf_counter(); enc.encode([t], 1, enc.qp); lat.append((time.perf_counter() - s) * 1000)
    qv = enc.encode(qtexts, 32, enc.qp)
    load_start = os.getloadavg()
    t1 = time.perf_counter()
    cv = enc.encode([c["text"] for c in chunks], 32, enc.pp)
    idx_s = time.perf_counter() - t1
    np.save(out / f"{name}.chunks.npy", cv); np.save(out / f"{name}.queries.npy", qv)
    (out / f"{name}.ids.json").write_text(json.dumps({"chunk_ids": [c["chunk_id"] for c in chunks], "qids": [q["qid"] for q in queries]}))
    perf = dict(model=name, int8=a.int8, loadavg_start=load_start, loadavg_end=os.getloadavg(), threads=a.threads, max_len=a.max_len, n_chunks=len(chunks), dim=int(cv.shape[1]),
                load_s=round(load_s, 2), index_s=round(idx_s, 1), chunks_per_s=round(len(chunks) / idx_s, 1),
                query_ms_p50=round(float(np.percentile(lat, 50)), 2), query_ms_p95=round(float(np.percentile(lat, 95)), 2),
                rss_mb_before=round(rss0, 1), rss_mb_after_load=round(rss_loaded, 1),
                peak_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                index_bytes_float32=int(cv.nbytes))
    (out / f"{name}.perf.json").write_text(json.dumps(perf, indent=1))
    print(json.dumps(perf))


if __name__ == "__main__":
    main()
