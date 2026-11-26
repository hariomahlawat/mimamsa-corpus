using System.Globalization;

namespace Mimamsa.Core.Search;

public readonly record struct Token(string Term, int Start, int End, int Position);

/// Tokenizer shared by the index, the query parser and the highlighter, so offsets always agree.
/// Tokens are maximal runs of letters, digits and combining marks (Devanagari matras stay inside the word);
/// everything else separates. Terms are lower-cased (invariant culture). No stemming at index time.
public static class Text
{
    static bool IsWordChar(char c)
    {
        if (char.IsLetterOrDigit(c)) return true;
        var cat = CharUnicodeInfo.GetUnicodeCategory(c);
        return cat is UnicodeCategory.NonSpacingMark or UnicodeCategory.SpacingCombiningMark;
    }

    public static List<Token> Tokenize(string s)
    {
        var list = new List<Token>();
        int i = 0, pos = 0;
        while (i < s.Length)
        {
            if (!IsWordChar(s[i])) { i++; continue; }
            int st = i;
            while (i < s.Length && IsWordChar(s[i])) i++;
            list.Add(new Token(s[st..i].Normalize(System.Text.NormalizationForm.FormC).ToLowerInvariant(), st, i, pos++));
        }
        return list;
    }

    public static readonly HashSet<string> Stopwords = new(StringComparer.Ordinal)
    {
        "a","an","the","and","or","of","to","in","on","at","by","for","with","from","as","is","are","was","were","be","been",
        "being","it","its","this","that","these","those","there","their","them","they","he","she","his","her","we","our","you",
        "your","i","me","my","can","could","would","should","shall","will","may","might","must","do","does","did","has","have",
        "had","not","no","nor","so","if","then","than","when","what","which","who","whom","whose","how","why","where","about",
        "into","over","under","up","down","out","any","all","some","such","only","own","same","very","just","also","someone",
        "anyone","nobody","somebody","them","him"
    };

    /// Light English suffix stripping used only to group surface forms for non-exact queries (never in exact: mode).
    public static string Stem(string t)
    {
        if (t.Length < 4 || !t.All(c => c is >= 'a' and <= 'z')) return t;
        if (t.EndsWith("ies") && t.Length > 4) return t[..^3] + "y";
        if (t.EndsWith("sses")) return t[..^2];
        if (t.EndsWith("ing") && t.Length > 5) return t[..^3];
        if (t.EndsWith("ed") && t.Length > 4) return t[..^2];
        if (t.EndsWith("es") && t.Length > 4 && (t[^3] is 's' or 'x' or 'z' || t.EndsWith("ches") || t.EndsWith("shes"))) return t[..^2];
        if (t.EndsWith('s') && !t.EndsWith("ss") && !t.EndsWith("us") && !t.EndsWith("is")) return t[..^1];
        return t;
    }
}
