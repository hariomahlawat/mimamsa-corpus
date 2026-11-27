# Linking the proposition register to the 658-source KB (v3.6)

The 658 records are a **research corpus** with `operational_clearance=false`, not a legally approved knowledge base. v3.4 identified 74 lexical candidate case-to-KB pairs and 14 specific priority KB records. None is a verified legal link.

A candidate may be promoted only after: (i) exact knowledge-record ID/claim fragment, (ii) source case/proposition ID, (iii) original PDF page and paragraph, (iv) applied statutory edition and effective date, (v) reasoned legal relevance and limits, (vi) negative later-treatment search, (vii) independent reviewer, and (viii) JAG outcome. Preserve **verified legal proposition** and **lexical search suggestion** as distinct relationship types.

Recommended API fields: `kb_id`, `claim_text_span`, `proposition_id`, `relation_type`, `source_sha256`, `source_pdf_page`, `paragraph_label`, `statute_version`, `applicability_date_range`, `verification_status`, `approver`, `approved_at`. No approved relation is created in this batch.

Cases outside core military law, particularly S.R. Dhingra, may remain searchable under a clearly segregated general public-service comparator heading but must not rank as an Army-law answer.
