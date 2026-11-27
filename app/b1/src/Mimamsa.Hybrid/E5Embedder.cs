// multilingual-e5-small (XLM-R tokenizer, 384-d, mean pooling, L2-normalised) through ONNX Runtime.
// E5 convention: queries are prefixed "query: ", passages "passage: ". CPU by default; CUDA EP only when asked and
// available (falls back to CPU, and Description says which one is in use).
using System.Security.Cryptography;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
using Microsoft.ML.Tokenizers;

namespace Mimamsa.Hybrid;

public sealed class E5Embedder : IDisposable
{
    /// Output width read from the model (384 for multilingual-e5-small, 768 for -base). C15: no longer fixed.
    public int Dim { get; }
    /// E5 family convention; configurable for models of the same tokenizer family with other prefixes.
    public string QueryPrefix { get; init; } = "query: ";
    public string PassagePrefix { get; init; } = "passage: ";
    readonly InferenceSession _session;
    readonly SentencePieceTokenizer _tok;
    readonly bool _tokenTypes;
    public string Device { get; }
    public string ModelSha256 { get; }
    /// Pad every batch to maxTokens (constant tensor shape). Set for DirectML, which recompiles on every new shape.
    public bool FixedLength { get; set; }

    // XLM-R (fairseq) vocabulary = SentencePiece ids shifted by one, with <s>=0, <pad>=1, </s>=2, <unk>=3.
    internal const long Bos = 0, Pad = 1, Eos = 2, Unk = 3;

    public E5Embedder(string modelDir, int threads = 0, bool tryCuda = false, string? expectedModelSha256 = null, bool tryDirectMl = false)
    {
        var onnx = Path.Combine(modelDir, "onnx", "model.onnx");
        ModelSha256 = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(onnx)));
        if (expectedModelSha256 is not null && !string.Equals(ModelSha256, expectedModelSha256, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Hybrid model file does not match the pinned SHA-256 (app/b1/hybrid/MODEL_MANIFEST.json).");
        using (var spm = File.OpenRead(Path.Combine(modelDir, "onnx", "sentencepiece.bpe.model")))
            _tok = SentencePieceTokenizer.Create(spm, false, false, null);
        var so = new SessionOptions { GraphOptimizationLevel = GraphOptimizationLevel.ORT_ENABLE_ALL };
        if (threads > 0) so.IntraOpNumThreads = threads;
        Device = "CPU";
        if (tryCuda)
        {
            try { so.AppendExecutionProvider_CUDA(0); Device = "CUDA"; }
            catch (Exception) { Device = "CPU (CUDA requested but unavailable)"; }
        }
        else if (tryDirectMl)
        {
            // DirectML (DX12 GPU, no CUDA toolkit). Needs the Microsoft.ML.OnnxRuntime.DirectML native package, used
            // by app/b1/bench only; the service's CPU package has no DML provider and falls back to CPU.
            try { so.EnableMemoryPattern = false; so.ExecutionMode = ExecutionMode.ORT_SEQUENTIAL; so.AppendExecutionProvider_DML(0); Device = "DirectML GPU"; FixedLength = true; }
            catch (Exception) { Device = "CPU (DirectML requested but unavailable)"; }
        }
        _session = new InferenceSession(onnx, so);
        _tokenTypes = _session.InputMetadata.ContainsKey("token_type_ids");
        Dim = _session.OutputMetadata.First().Value.Dimensions.Last();
    }

    /// Token ids in the model's vocabulary: [&lt;s&gt;] + pieces + [&lt;/s&gt;], truncated to maxTokens.
    internal long[] Encode(string text, int maxTokens)
    {
        // Input convention (also applied by app/b1/hybrid/tokenizer_vectors.py): whitespace runs collapse to one space
        // and ends are trimmed. ML.Tokenizers and HF `tokenizers` differ on raw tab/newline/trailing-space runs.
        text = System.Text.RegularExpressions.Regex.Replace(text, @"\s+", " ").Trim();
        var ids = _tok.EncodeToIds(text, false, false, true, true);
        int n = Math.Min(ids.Count, maxTokens - 2);
        var r = new long[n + 2];
        r[0] = Bos;
        for (int i = 0; i < n; i++) r[i + 1] = ids[i] == 0 ? Unk : ids[i] + 1;
        r[n + 1] = Eos;
        return r;
    }

    public float[] EmbedQuery(string q) => Embed(new[] { QueryPrefix + q }, 128)[0];

    public float[][] Embed(IReadOnlyList<string> texts, int maxTokens)
    {
        var enc = texts.Select(t => Encode(t, maxTokens)).ToArray();
        int b = enc.Length, len = FixedLength ? maxTokens : enc.Max(e => e.Length);
        var ids = new DenseTensor<long>(new[] { b, len });
        var mask = new DenseTensor<long>(new[] { b, len });
        var types = new DenseTensor<long>(new[] { b, len });
        for (int i = 0; i < b; i++)
            for (int j = 0; j < len; j++)
            {
                bool on = j < enc[i].Length;
                ids[i, j] = on ? enc[i][j] : Pad;
                mask[i, j] = on ? 1 : 0;
            }
        var inputs = new List<NamedOnnxValue> { NamedOnnxValue.CreateFromTensor("input_ids", ids), NamedOnnxValue.CreateFromTensor("attention_mask", mask) };
        if (_tokenTypes) inputs.Add(NamedOnnxValue.CreateFromTensor("token_type_ids", types));
        using var outs = _session.Run(inputs);
        var h = outs.First().AsTensor<float>();   // [b, len, 384] last_hidden_state
        var res = new float[b][];
        for (int i = 0; i < b; i++)
        {
            var v = new float[Dim];
            int n = enc[i].Length;
            for (int j = 0; j < n; j++)
                for (int k = 0; k < Dim; k++) v[k] += h[i, j, k];
            double norm = 0;
            for (int k = 0; k < Dim; k++) { v[k] /= n; norm += v[k] * v[k]; }
            norm = Math.Sqrt(norm);
            for (int k = 0; k < Dim; k++) v[k] = (float)(v[k] / norm);
            res[i] = v;
        }
        return res;
    }

    public void Dispose() => _session.Dispose();
}
