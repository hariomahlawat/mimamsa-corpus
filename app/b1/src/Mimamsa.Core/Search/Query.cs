// Professional query syntax (app/design/03_RESEARCH_WORKSPACE.md §2): AND / OR / NOT (upper case), parentheses,
// "phrases", NEAR/n, prefix*, field:value (title party judge court bench case citation section act type date year),
// ranges a..b, and the exact: prefix (lexical only; no abbreviation expansion, no stem grouping).
// Default operator between clauses is AND once any syntax is used. A query with no syntax at all is "plain words".
// A malformed query is never relaxed silently: ParseException carries the position for the UI.
namespace Mimamsa.Core.Search;

public sealed class ParseException(string message, int position) : Exception(message) { public int Position { get; } = position; }

public abstract record QNode;
public sealed record QTerm(string Term, bool Prefix) : QNode;
public sealed record QPhrase(IReadOnlyList<string> Terms, string Display) : QNode;
public sealed record QAnd(IReadOnlyList<QNode> Items) : QNode;
public sealed record QOr(IReadOnlyList<QNode> Items) : QNode;
public sealed record QNot(QNode Item) : QNode;
public sealed record QNear(QNode Left, QNode Right, int Distance) : QNode;
public sealed record QField(string Field, string Value, IReadOnlyList<string> Terms, string? RangeFrom, string? RangeTo) : QNode;

public sealed record ParsedQuery(string Raw, bool Exact, bool Plain, QNode? Root, IReadOnlyList<string> PlainWords);

public static class QueryParser
{
    public static readonly HashSet<string> Fields = new(StringComparer.OrdinalIgnoreCase)
    { "title", "party", "judge", "court", "bench", "case", "citation", "section", "act", "type", "date", "year", "rule" };

    enum K { LParen, RParen, Quoted, Word, And, Or, Not, Near, Field, End }
    sealed record Tok(K Kind, string Text, int Pos, int N = 0);

    public static ParsedQuery Parse(string raw)
    {
        raw ??= "";
        var s = raw.Trim();
        int offset = raw.Length - raw.TrimStart().Length;
        bool exact = false;
        if (s.StartsWith("exact:", StringComparison.OrdinalIgnoreCase)) { exact = true; s = s[6..]; offset += 6; }
        if (s.Trim().Length == 0) throw new ParseException("The query is empty.", offset);
        var toks = Lex(s, offset);
        bool syntax = exact || toks.Any(t => t.Kind is K.LParen or K.RParen or K.Quoted or K.And or K.Or or K.Not or K.Near or K.Field)
                      || toks.Any(t => t.Kind == K.Word && t.Text.EndsWith('*'));
        if (!syntax)
            return new ParsedQuery(raw, false, true, null, toks.Where(t => t.Kind == K.Word).Select(t => t.Text).ToList());
        int i = 0;
        var root = ParseOr(toks, ref i);
        if (toks[i].Kind != K.End)
            throw toks[i].Kind == K.RParen ? new ParseException("Closing parenthesis without a matching opening one.", toks[i].Pos)
                                           : new ParseException("Unexpected text.", toks[i].Pos);
        return new ParsedQuery(raw, exact, false, root, Array.Empty<string>());
    }

    /// Plain-words fallback after the user confirms (RET-13): syntax characters become spaces.
    public static ParsedQuery PlainWords(string raw)
    {
        var s = raw.Trim();
        if (s.StartsWith("exact:", StringComparison.OrdinalIgnoreCase)) s = s[6..];
        var cleaned = new string(s.Select(c => c is '(' or ')' or '"' or '*' or ':' ? ' ' : c).ToArray());
        var words = cleaned.Split(' ', StringSplitOptions.RemoveEmptyEntries)
                           .Where(w => w is not ("AND" or "OR" or "NOT") && !w.StartsWith("NEAR/")).ToList();
        if (words.Count == 0) throw new ParseException("No words left to search.", 0);
        return new ParsedQuery(raw, false, true, null, words);
    }

    static List<Tok> Lex(string s, int off)
    {
        var list = new List<Tok>();
        int i = 0;
        while (i < s.Length)
        {
            char c = s[i];
            if (char.IsWhiteSpace(c)) { i++; continue; }
            if (c == '(') { list.Add(new Tok(K.LParen, "(", off + i)); i++; continue; }
            if (c == ')') { list.Add(new Tok(K.RParen, ")", off + i)); i++; continue; }
            if (c == '"')
            {
                int close = s.IndexOf('"', i + 1);
                if (close < 0) throw new ParseException("Quotation mark is not closed.", off + i);
                list.Add(new Tok(K.Quoted, s[(i + 1)..close], off + i));
                i = close + 1; continue;
            }
            // A word may carry attached sub-clause parentheses ("8(3)(a)", "W.P.(C)"): '(' opens a group only at the
            // start of a token; inside a word, balanced parentheses belong to the word.
            int st = i, depth = 0;
            while (i < s.Length && !char.IsWhiteSpace(s[i]) && s[i] != '"')
            {
                if (s[i] == '(') depth++;
                else if (s[i] == ')') { if (depth == 0) break; depth--; }
                i++;
            }
            if (depth > 0) throw new ParseException("Parenthesis inside a word is not closed.", off + st);
            var w = s[st..i];
            // field:value, field:"phrase" or field:a..b
            int colon = w.IndexOf(':');
            if (colon > 0 && Fields.Contains(w[..colon]))
            {
                var name = w[..colon].ToLowerInvariant();
                var val = w[(colon + 1)..];
                if (val.Length == 0 && i < s.Length && s[i] == '"')
                {
                    int close = s.IndexOf('"', i + 1);
                    if (close < 0) throw new ParseException("Quotation mark is not closed.", off + i);
                    val = s[(i + 1)..close]; i = close + 1;
                }
                if (val.Length == 0) throw new ParseException($"Field '{name}' needs a value.", off + st);
                list.Add(new Tok(K.Field, name + "\u0001" + val, off + st));
                continue;
            }
            if (w == "AND") list.Add(new Tok(K.And, w, off + st));
            else if (w == "OR") list.Add(new Tok(K.Or, w, off + st));
            else if (w == "NOT") list.Add(new Tok(K.Not, w, off + st));
            else if (w.StartsWith("NEAR/"))
            {
                if (!int.TryParse(w[5..], out var n) || n < 1 || n > 100) throw new ParseException("NEAR needs a distance from 1 to 100, e.g. NEAR/5.", off + st);
                list.Add(new Tok(K.Near, w, off + st, n));
            }
            else list.Add(new Tok(K.Word, w, off + st));
        }
        list.Add(new Tok(K.End, "", off + s.Length));
        return list;
    }

    static QNode ParseOr(List<Tok> t, ref int i)
    {
        var items = new List<QNode> { ParseAnd(t, ref i) };
        while (t[i].Kind == K.Or) { i++; items.Add(ParseAnd(t, ref i)); }
        return items.Count == 1 ? items[0] : new QOr(items);
    }

    static QNode ParseAnd(List<Tok> t, ref int i)
    {
        var items = new List<QNode> { ParseUnary(t, ref i) };
        while (true)
        {
            if (t[i].Kind == K.And) { i++; items.Add(ParseUnary(t, ref i)); continue; }
            if (t[i].Kind is K.Word or K.Quoted or K.LParen or K.Not or K.Field) { items.Add(ParseUnary(t, ref i)); continue; }
            break;
        }
        return items.Count == 1 ? items[0] : new QAnd(items);
    }

    static QNode ParseUnary(List<Tok> t, ref int i)
    {
        if (t[i].Kind == K.Not) { i++; return new QNot(ParseUnary(t, ref i)); }
        var left = ParsePrimary(t, ref i);
        while (t[i].Kind == K.Near) { int n = t[i].N; i++; left = new QNear(left, ParsePrimary(t, ref i), n); }
        return left;
    }

    static QNode ParsePrimary(List<Tok> t, ref int i)
    {
        var tok = t[i];
        switch (tok.Kind)
        {
            case K.LParen:
                i++;
                var inner = ParseOr(t, ref i);
                if (t[i].Kind != K.RParen) throw new ParseException("Opening parenthesis is not closed.", tok.Pos);
                i++; return inner;
            case K.Quoted:
                i++;
                var pt = Text.Tokenize(tok.Text).Select(x => x.Term).ToList();
                if (pt.Count == 0) throw new ParseException("Empty phrase.", tok.Pos);
                return pt.Count == 1 ? new QTerm(pt[0], false) : new QPhrase(pt, tok.Text);
            case K.Word:
                i++;
                return WordNode(tok.Text, tok.Pos);
            case K.Field:
            {
                i++;
                var parts = tok.Text.Split('\u0001', 2);
                string? from = null, to = null;
                int dots = parts[1].IndexOf("..", StringComparison.Ordinal);
                if (dots >= 0) { from = parts[1][..dots]; to = parts[1][(dots + 2)..]; }
                return new QField(parts[0] == "rule" ? "section" : parts[0], parts[1],
                                  Text.Tokenize(parts[1]).Select(x => x.Term).ToList(), from, to);
            }
            case K.End: throw new ParseException("The query ends where a search term was expected.", tok.Pos);
            default: throw new ParseException($"'{tok.Text}' needs a search term on both sides.", tok.Pos);
        }
    }

    static QNode WordNode(string w, int pos)
    {
        bool prefix = w.EndsWith('*');
        var core = prefix ? w[..^1] : w;
        var toks = Text.Tokenize(core).Select(x => x.Term).ToList();
        if (toks.Count == 0) throw new ParseException("A search term has no letters or digits.", pos);
        if (prefix)
        {
            if (toks.Count != 1 || toks[0].Length < 3) throw new ParseException("A prefix search needs at least 3 letters before *.", pos);
            return new QTerm(toks[0], true);
        }
        return toks.Count == 1 ? new QTerm(toks[0], false) : new QPhrase(toks, core);
    }
}
