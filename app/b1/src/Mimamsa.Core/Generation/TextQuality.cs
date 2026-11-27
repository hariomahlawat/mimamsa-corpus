// Language identification and extracted-text reliability (C14 F07), computed deterministically from the verified
// derivative at generation load. Nothing is repaired or re-extracted: the result only labels the text.
//
// Script share decides the detected language. The reliability test targets the legacy (non-Unicode) Devanagari font
// encodings found in India Code Hindi PDFs: when such a text layer is extracted, dependent vowel signs and the virama
// land at the start of words ("िारा" for "धारा"). In well-formed Unicode Hindi a word never begins with a dependent
// sign, so the share of Devanagari words that do is a direct signature. Measured on the B1 sample: well-formed Hindi
// copies (BNS/BNSS/BSA Hindi editions) 0.000-0.001; legacy-font copies 0.033-0.545.
namespace Mimamsa.Core.Generation;

public sealed record TextAssessment(string DetectedLanguage, string Reliability, string Basis, int DevanagariWords, double SignatureRatio);

public static class TextQuality
{
    public const double SignatureThreshold = 0.01;   // share of Devanagari words that begin with a dependent sign
    public const int MinDevanagariWords = 200;       // below this the signature is not assessed (too little text)
    public const string Reliable = "reliable", PartlyUnreliable = "partly_unreliable", Unreliable = "unreliable", NoText = "no_text";

    static bool IsDeva(char c) => c >= 'ऀ' && c <= 'ॿ';
    // dependent vowel signs, virama, nukta-less modifiers that cannot start a well-formed word
    static bool IsDependentSign(char c) => (c >= 'ऺ' && c <= 'ॏ') || c is 'ऀ' or 'ँ' or 'ं' or 'ः' or 'ॢ' or 'ॣ';

    public static TextAssessment Assess(IEnumerable<string> pages)
    {
        long latin = 0, deva = 0; int devaWords = 0, signStart = 0;
        foreach (var text in pages)
        {
            bool inDeva = false;
            foreach (var c in text)
            {
                if (IsDeva(c))
                {
                    deva++;
                    if (!inDeva) { devaWords++; if (IsDependentSign(c)) signStart++; inDeva = true; }
                }
                else
                {
                    inDeva = false;
                    if (c < 'ɐ' && char.IsLetter(c)) latin++;
                }
            }
        }
        long letters = latin + deva;
        if (letters == 0) return new TextAssessment("none", NoText, "No extracted text.", 0, 0);
        double devaShare = (double)deva / letters;
        string lang = devaShare >= 0.5 ? "hi" : devaShare >= 0.05 ? "en+hi" : "en";
        double ratio = devaWords == 0 ? 0 : (double)signStart / devaWords;
        if (devaWords < MinDevanagariWords)
            return new TextAssessment(lang, Reliable, devaWords == 0 ? "No Devanagari text; script check not applicable."
                : $"{devaWords:N0} Devanagari words: too few to assess the legacy-font signature.", devaWords, ratio);
        bool garbled = ratio >= SignatureThreshold;
        string basis = $"{ratio:P1} of {devaWords:N0} Devanagari words begin with a dependent vowel sign or virama " +
                       $"(legacy-font signature; threshold {SignatureThreshold:P0}).";
        string state = !garbled ? Reliable : devaShare >= 0.5 ? Unreliable : PartlyUnreliable;
        return new TextAssessment(lang, state, basis, devaWords, ratio);
    }

    public static void Apply(DocumentRecord d)
    {
        var a = Assess(d.Pages.Values.OrderBy(p => p.Page).Select(p => p.Text));
        d.TextAssessment = a;
    }
}
