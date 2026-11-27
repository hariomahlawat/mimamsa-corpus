// C16 B06: canonical JSON (contract section 9) for journal records, the activation log and the scenario binding hash.
// Keys sorted by code point, separators "," and ":" without whitespace, non-ASCII written as itself, integers only
// (the journal never carries floats). Matches Python json.dumps(sort_keys=True, ensure_ascii=False,
// separators=(",", ":")) for the value shapes used here.
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Mimamsa.Core.Activation;

public static class CanonicalJson
{
    public static byte[] Bytes(JsonNode? node)
    {
        var sb = new StringBuilder();
        Write(sb, node);
        return Encoding.UTF8.GetBytes(sb.ToString());
    }

    public static string Sha256Hex(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    public static string RecordSha256(JsonNode? node) => Sha256Hex(Bytes(node));

    static void Write(StringBuilder sb, JsonNode? node)
    {
        switch (node)
        {
            case null: sb.Append("null"); break;
            case JsonObject o:
                sb.Append('{');
                bool first = true;
                foreach (var kv in o.OrderBy(k => k.Key, StringComparer.Ordinal))
                {
                    if (!first) sb.Append(',');
                    first = false;
                    WriteString(sb, kv.Key);
                    sb.Append(':');
                    Write(sb, kv.Value);
                }
                sb.Append('}');
                break;
            case JsonArray a:
                sb.Append('[');
                for (int i = 0; i < a.Count; i++) { if (i > 0) sb.Append(','); Write(sb, a[i]); }
                sb.Append(']');
                break;
            case JsonValue v:
                if (v.TryGetValue<JsonElement>(out var el)) WriteElement(sb, el);
                else if (v.TryGetValue<string>(out var s)) WriteString(sb, s);
                else if (v.TryGetValue<bool>(out var bo)) sb.Append(bo ? "true" : "false");
                else if (v.TryGetValue<long>(out var lo)) sb.Append(lo.ToString(CultureInfo.InvariantCulture));
                else if (v.TryGetValue<int>(out var io)) sb.Append(io.ToString(CultureInfo.InvariantCulture));
                else WriteElement(sb, JsonSerializer.SerializeToElement(v));
                break;
        }
    }

    static void WriteElement(StringBuilder sb, JsonElement el)
    {
        switch (el.ValueKind)
        {
            case JsonValueKind.String: WriteString(sb, el.GetString()!); break;
            case JsonValueKind.True: sb.Append("true"); break;
            case JsonValueKind.False: sb.Append("false"); break;
            case JsonValueKind.Null: sb.Append("null"); break;
            case JsonValueKind.Number:
                if (el.TryGetInt64(out var l)) { sb.Append(l.ToString(CultureInfo.InvariantCulture)); break; }
                var d = el.GetDouble();
                if (double.IsFinite(d) && Math.Floor(d) == d && Math.Abs(d) < 9007199254740992d) { sb.Append(((long)d).ToString(CultureInfo.InvariantCulture)); break; }
                throw new FormatException("canonical JSON in the activation journal carries integers only");
            case JsonValueKind.Object: Write(sb, JsonObject.Create(el)); break;
            case JsonValueKind.Array: Write(sb, JsonArray.Create(el)); break;
            default: throw new FormatException("unsupported JSON value");
        }
    }

    static void WriteString(StringBuilder sb, string s)
    {
        sb.Append('"');
        foreach (var ch in s)
        {
            switch (ch)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                case '\b': sb.Append("\\b"); break;
                case '\f': sb.Append("\\f"); break;
                default:
                    if (ch < 0x20) sb.Append("\\u").Append(((int)ch).ToString("x4", CultureInfo.InvariantCulture));
                    else sb.Append(ch);
                    break;
            }
        }
        sb.Append('"');
    }

    /// Parse JSON refusing duplicate keys anywhere (the Python side uses object_pairs_hook=_no_dupes).
    public static JsonNode ParseStrict(ReadOnlySpan<byte> utf8)
    {
        var reader = new Utf8JsonReader(utf8, new JsonReaderOptions { CommentHandling = JsonCommentHandling.Disallow, AllowTrailingCommas = false });
        using var doc = JsonDocument.ParseValue(ref reader);
        if (reader.Read()) throw new FormatException("trailing content after JSON value");
        CheckNoDuplicates(doc.RootElement);
        return JsonNode.Parse(doc.RootElement.GetRawText())!;
    }

    static void CheckNoDuplicates(JsonElement el)
    {
        if (el.ValueKind == JsonValueKind.Object)
        {
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var p in el.EnumerateObject())
            {
                if (!seen.Add(p.Name)) throw new FormatException($"duplicate key {p.Name}");
                CheckNoDuplicates(p.Value);
            }
        }
        else if (el.ValueKind == JsonValueKind.Array)
            foreach (var x in el.EnumerateArray()) CheckNoDuplicates(x);
    }
}
