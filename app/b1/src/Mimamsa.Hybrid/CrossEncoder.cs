// C15 WP2: cross-encoder reranker (cross-encoder/mmarco-mMiniLMv2-L12-H384-v1, Apache-2.0, multilingual, XLM-R
// vocabulary) through ONNX Runtime on CPU. It scores (query, passage) pairs jointly; the score is a logit whose native
// decision boundary is 0 (sigmoid 0.5), set by the model's training, not by this project's data. Scores describe
// textual relevance only, never legal relevance or authority.
using System.Security.Cryptography;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
using Microsoft.ML.Tokenizers;

namespace Mimamsa.Hybrid;

public sealed class CrossEncoder : Mimamsa.Core.Search.IReranker, IDisposable
{
    readonly InferenceSession _session;
    readonly SentencePieceTokenizer _tok;
    readonly bool _tokenTypes;
    public string ModelSha256 { get; }
    public string Label { get; }

    public CrossEncoder(string modelDir, string onnxFile = "onnx/model.onnx", string? expectedSha256 = null, int threads = 0, string label = "mmarco-mMiniLMv2-L12-H384-v1")
    {
        var onnx = Path.Combine(modelDir, onnxFile);
        ModelSha256 = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(onnx)));
        if (expectedSha256 is not null && !string.Equals(ModelSha256, expectedSha256, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Reranker model file does not match the pinned SHA-256 (app/b1/hybrid/manifests).");
        using (var spm = File.OpenRead(Path.Combine(modelDir, "sentencepiece.bpe.model")))
            _tok = SentencePieceTokenizer.Create(spm, false, false, null);
        var so = new SessionOptions { GraphOptimizationLevel = GraphOptimizationLevel.ORT_ENABLE_ALL };
        if (threads > 0) so.IntraOpNumThreads = threads;
        _session = new InferenceSession(onnx, so);
        _tokenTypes = _session.InputMetadata.ContainsKey("token_type_ids");
        Label = $"{label} ({Path.GetFileName(onnxFile)}, CPU)";
    }

    long[] Pieces(string text)
    {
        text = System.Text.RegularExpressions.Regex.Replace(text, @"\s+", " ").Trim();
        var ids = _tok.EncodeToIds(text, false, false, true, true);
        var r = new long[ids.Count];
        for (int i = 0; i < ids.Count; i++) r[i] = ids[i] == 0 ? E5Embedder.Unk : ids[i] + 1;   // fairseq XLM-R id shift
        return r;
    }

    /// XLM-R pair encoding: &lt;s&gt; query &lt;/s&gt;&lt;/s&gt; passage &lt;/s&gt;, passage truncated to fit maxTokens.
    internal long[] EncodePair(string query, string passage, int maxTokens)
    {
        var q = Pieces(query); var p = Pieces(passage);
        int qn = Math.Min(q.Length, 64);
        int pn = Math.Max(0, Math.Min(p.Length, maxTokens - qn - 4));
        var r = new long[qn + pn + 4];
        int k = 0;
        r[k++] = E5Embedder.Bos;
        for (int i = 0; i < qn; i++) r[k++] = q[i];
        r[k++] = E5Embedder.Eos; r[k++] = E5Embedder.Eos;
        for (int i = 0; i < pn; i++) r[k++] = p[i];
        r[k] = E5Embedder.Eos;
        return r;
    }

    /// Relevance logits for each passage against the query (same order as `passages`).
    public float[] Score(string query, IReadOnlyList<string> passages, int maxTokens = 256, int batch = 16)
    {
        var res = new float[passages.Count];
        for (int s = 0; s < passages.Count; s += batch)
        {
            var enc = passages.Skip(s).Take(batch).Select(p => EncodePair(query, p, maxTokens)).ToArray();
            int b = enc.Length, len = enc.Max(e => e.Length);
            var ids = new DenseTensor<long>(new[] { b, len });
            var mask = new DenseTensor<long>(new[] { b, len });
            var types = new DenseTensor<long>(new[] { b, len });
            for (int i = 0; i < b; i++)
                for (int j = 0; j < len; j++)
                {
                    bool on = j < enc[i].Length;
                    ids[i, j] = on ? enc[i][j] : E5Embedder.Pad;
                    mask[i, j] = on ? 1 : 0;
                }
            var inputs = new List<NamedOnnxValue> { NamedOnnxValue.CreateFromTensor("input_ids", ids), NamedOnnxValue.CreateFromTensor("attention_mask", mask) };
            if (_tokenTypes) inputs.Add(NamedOnnxValue.CreateFromTensor("token_type_ids", types));
            using var outs = _session.Run(inputs);
            var logits = outs.First().AsTensor<float>();   // [b, 1]
            for (int i = 0; i < b; i++) res[s + i] = logits[i, 0];
        }
        return res;
    }

    public string Description => Label;
    float[] Mimamsa.Core.Search.IReranker.Score(string query, IReadOnlyList<string> passages) => Score(query, passages, MaxTokens);
    public int MaxTokens { get; init; } = 256;

    public void Dispose() => _session.Dispose();
}
