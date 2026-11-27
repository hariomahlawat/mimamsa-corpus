// C16 B03: canonical JSON (contract §9.1), a port of app/contract/mimamsa_contract/c16/canonical.py.
// The bytes must equal Python's json.dumps(_check(obj), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
// encoded as UTF-8 (cross-language golden tests: KnowledgeRowsTests). Rules:
//   - object keys sorted by Unicode code point; no whitespace; non-ASCII written as itself;
//   - strings must already be NFC (rejected, never normalised); lone surrogates are rejected (Python cannot encode them);
//   - escapes as Python: \" \\ \n \r \t \b \f, other C0 controls as \u00xx (lower-case hex); nothing else escaped;
//   - integers within ±(2^53-1); floats finite, not -0.0, at most 4 decimal places, |x| < 1e15 unless integral,
//     written as an integer when integral (12.0 -> 12), otherwise as the shortest round-trip decimal (Python repr).
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Knowledge;

public sealed class CanonicalException(string message) : Exception(message);

public static class CanonicalJson
{
    public const long MaxSafeInt = (1L << 53) - 1;
    static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    public static byte[] Bytes(JsonNode? node)
    {
        var sb = new StringBuilder();
        Write(sb, node, "$");
        return StrictUtf8.GetBytes(sb.ToString());
    }

    public static string Text(JsonNode? node) => StrictUtf8.GetString(Bytes(node));

    public static string RecordSha256(JsonNode? node) => Sha256Hex(Bytes(node));

    public static string Sha256Hex(ReadOnlySpan<byte> data) => Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();

    /// Python str ordering: by Unicode code point (UTF-16 ordinal order differs only for surrogates vs U+E000..U+FFFF).
    public static int CompareCodePoints(string? a, string? b)
    {
        if (ReferenceEquals(a, b)) return 0;
        if (a is null) return -1;
        if (b is null) return 1;
        int n = Math.Min(a.Length, b.Length);
        for (int i = 0; i < n; i++)
        {
            char x = a[i], y = b[i];
            if (x == y) continue;
            bool xs = char.IsSurrogate(x), ys = char.IsSurrogate(y);
            if (xs == ys) return x.CompareTo(y);
            return xs ? 1 : -1;     // a surrogate encodes a code point above U+FFFF
        }
        return a.Length.CompareTo(b.Length);
    }

    public static readonly IComparer<string> CodePointComparer = Comparer<string>.Create(CompareCodePoints);

    static void Write(StringBuilder sb, JsonNode? node, string path)
    {
        switch (node)
        {
            case null:
                sb.Append("null");
                return;
            case JsonObject o:
            {
                var props = o.ToList();
                props.Sort((p, q) => CompareCodePoints(p.Key, q.Key));
                sb.Append('{');
                for (int i = 0; i < props.Count; i++)
                {
                    if (i > 0) sb.Append(',');
                    CheckString(props[i].Key, path);
                    WriteString(sb, props[i].Key);
                    sb.Append(':');
                    Write(sb, props[i].Value, path + "." + props[i].Key);
                }
                sb.Append('}');
                return;
            }
            case JsonArray a:
                sb.Append('[');
                for (int i = 0; i < a.Count; i++)
                {
                    if (i > 0) sb.Append(',');
                    Write(sb, a[i], $"{path}[{i}]");
                }
                sb.Append(']');
                return;
            case JsonValue v:
                WriteValue(sb, v, path);
                return;
            default:
                throw new CanonicalException($"{path}: unsupported node");
        }
    }

    static void WriteValue(StringBuilder sb, JsonValue v, string path)
    {
        if (v.TryGetValue<JsonElement>(out var el))
        {
            switch (el.ValueKind)
            {
                case JsonValueKind.Null: sb.Append("null"); return;
                case JsonValueKind.True: sb.Append("true"); return;
                case JsonValueKind.False: sb.Append("false"); return;
                case JsonValueKind.String:
                {
                    var s = el.GetString()!;
                    CheckString(s, path); WriteString(sb, s); return;
                }
                case JsonValueKind.Number: WriteNumberText(sb, el.GetRawText(), path); return;
                default: throw new CanonicalException($"{path}: unsupported JSON element");
            }
        }
        if (v.TryGetValue<string>(out var str)) { CheckString(str, path); WriteString(sb, str); return; }
        if (v.TryGetValue<bool>(out var b)) { sb.Append(b ? "true" : "false"); return; }
        if (v.TryGetValue<int>(out var i32)) { WriteInteger(sb, i32, path); return; }
        if (v.TryGetValue<long>(out var i64)) { WriteInteger(sb, i64, path); return; }
        if (v.TryGetValue<double>(out var d)) { WriteDouble(sb, d, path); return; }
        throw new CanonicalException($"{path}: unsupported value type");
    }

    static void WriteNumberText(StringBuilder sb, string raw, string path)
    {
        if (raw.IndexOfAny(['.', 'e', 'E']) < 0)
        {
            var big = BigInteger.Parse(raw, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture);
            if (BigInteger.Abs(big) > MaxSafeInt) throw new CanonicalException($"{path}: integer outside the safe range");
            sb.Append(((long)big).ToString(CultureInfo.InvariantCulture));
            return;
        }
        WriteDouble(sb, double.Parse(raw, NumberStyles.Float, CultureInfo.InvariantCulture), path);
    }

    static void WriteInteger(StringBuilder sb, long x, string path)
    {
        if (x > MaxSafeInt || x < -MaxSafeInt) throw new CanonicalException($"{path}: integer outside the safe range");
        sb.Append(x.ToString(CultureInfo.InvariantCulture));
    }

    static void WriteDouble(StringBuilder sb, double x, string path)
    {
        if (!double.IsFinite(x)) throw new CanonicalException($"{path}: non-finite number");
        if (x == 0 && double.IsNegative(x)) throw new CanonicalException($"{path}: negative zero");
        if (Math.Floor(x) == x)
        {
            if (Math.Abs(x) > MaxSafeInt) throw new CanonicalException($"{path}: integer outside the safe range");
            WriteInteger(sb, (long)x, path);
            return;
        }
        if (Math.Abs(x) >= 1e15) throw new CanonicalException($"{path}: float magnitude too large");
        // round(x, 4) == x  <=>  the shortest round-trip decimal has at most 4 fractional digits
        var r = x.ToString("R", CultureInfo.InvariantCulture);
        if (r.Contains('E')) throw new CanonicalException($"{path}: more than 4 decimal places");
        int dot = r.IndexOf('.');
        if (dot >= 0 && r.Length - dot - 1 > 4) throw new CanonicalException($"{path}: more than 4 decimal places");
        sb.Append(r);
    }

    static void CheckString(string s, string path)
    {
        for (int i = 0; i < s.Length; i++)
        {
            char c = s[i];
            if (char.IsHighSurrogate(c) && i + 1 < s.Length && char.IsLowSurrogate(s[i + 1])) { i++; continue; }
            if (char.IsSurrogate(c)) throw new CanonicalException($"{path}: lone surrogate");
        }
        if (!s.IsNormalized(NormalizationForm.FormC)) throw new CanonicalException($"{path}: string is not NFC");
    }

    static void WriteString(StringBuilder sb, string s)
    {
        sb.Append('"');
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                case '\b': sb.Append("\\b"); break;
                case '\f': sb.Append("\\f"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    else sb.Append(c);
                    break;
            }
        }
        sb.Append('"');
    }
}
