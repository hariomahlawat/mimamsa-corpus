namespace Mimamsa.Core.Search;

/// Excerpt from the verified passage text (never generated), with highlight ranges relative to the excerpt.
public sealed record Snippet(string Text, IReadOnlyList<int[]> Highlights, bool TruncatedStart, bool TruncatedEnd, int PassageCharStart);

public static class Snippets
{
    public static List<(int s, int e)> Marks(string text, IReadOnlyCollection<string> terms, IReadOnlyList<IReadOnlyList<string>> phrases)
    {
        var toks = Text.Tokenize(text);
        var marks = new List<(int, int)>();
        var termSet = terms as HashSet<string> ?? terms.ToHashSet(StringComparer.Ordinal);
        foreach (var t in toks) if (termSet.Contains(t.Term)) marks.Add((t.Start, t.End));
        foreach (var ph in phrases.Where(p => p.Count > 0))
            for (int i = 0; i + ph.Count <= toks.Count; i++)
            {
                bool ok = true;
                for (int k = 0; k < ph.Count && ok; k++) ok = toks[i + k].Term == ph[k];
                if (ok) marks.Add((toks[i].Start, toks[i + ph.Count - 1].End));
            }
        marks.Sort();
        var merged = new List<(int s, int e)>();
        foreach (var m in marks)
            if (merged.Count > 0 && m.Item1 <= merged[^1].e + 1) merged[^1] = (merged[^1].s, Math.Max(merged[^1].e, m.Item2));
            else merged.Add(m);
        return merged;
    }

    public static Snippet Build(string text, IReadOnlyCollection<string> terms, IReadOnlyList<IReadOnlyList<string>> phrases, int width = 340)
    {
        var marks = Marks(text, terms, phrases);
        int center = marks.Count > 0 ? marks[0].s : 0;
        int start = Math.Max(0, center - width / 3);
        if (start > 0) { int sp = text.LastIndexOfAny(new[] { ' ', '\n' }, start); start = sp >= 0 && start - sp < 40 ? sp + 1 : start; }
        int end = Math.Min(text.Length, start + width);
        if (end < text.Length) { int sp = text.IndexOfAny(new[] { ' ', '\n' }, end); end = sp >= 0 && sp - end < 40 ? sp : end; }
        var raw = text[start..end];
        // collapse whitespace while keeping highlight offsets aligned
        var sb = new System.Text.StringBuilder(raw.Length);
        var map = new int[raw.Length + 1];
        bool ws = false;
        for (int i = 0; i < raw.Length; i++)
        {
            map[i] = sb.Length;
            if (char.IsWhiteSpace(raw[i])) { if (!ws && sb.Length > 0) sb.Append(' '); ws = true; }
            else { sb.Append(raw[i]); ws = false; }
        }
        map[raw.Length] = sb.Length;
        var hl = marks.Where(m => m.s >= start && m.e <= end).Select(m => new[] { map[m.s - start], map[m.e - start] }).ToList();
        return new Snippet(sb.ToString().TrimEnd(), hl, start > 0, end < text.Length, start);
    }
}
