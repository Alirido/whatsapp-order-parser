# What a correct parse must contain

These answers assume **today is Wednesday 2026-11-18**. Hard-code that date
while testing (`TODAY = date(2026, 11, 18)`), so "besok", "lusa" and "Senin"
always resolve the same way and you can compare runs.

Rule for every message: anything the customer didn't say must be `null`, never
guessed, and the admin should get a question about it.

| # | Intent | Must contain | Traps |
|---|---|---|---|
| 1 | new_order | Besi beton polos 10 mm × 20 batang; wiremesh M8 × 5 lembar; delivery to Jl. Gegerkalong Hilir No. 45; date 2026-11-19, morning; name Pak Budi; phone 081200001234 | Abbreviations: "btg", "a.n." (atas nama = in the name of) |
| 2 | new_order | Semen Tiga Roda × 40 sak; pasir × 1 truk; bata merah × 2000 pcs; delivery to Jl. Setiabudi 210; date 2026-11-23 (Monday); payment: transfer; name Ibu Rina, company CV Karya Bangun | Resolving "hari Senin" to a date |
| 3 | question (or a conditional order) | Hollow 4x4 × 30 batang as a *conditional* item; a question for the admin about price and stock | It's not a confirmed order. No address, no name: all null, not invented |
| 4 | question | No items. The customer asks tomorrow's opening hours | Must not create an order |
| 5 | change_order | Cancel besi 12 mm; add besi 13 mm with the *same quantity as before*; quantity = null plus a question | "jumlahnya sama" refers to an order this message doesn't contain. The quantity is unknown |
| 6 | new_order | Besi 8 mm × 50 batang; besi 10 mm × **30** batang (not 25); kawat bendrat × 2 rol; delivery, date 2026-11-20 (lusa), afternoon; name Pak Asep; area Cijerah, exact address unknown | Self-correction "25 eh 30". "ke rumah" means the address must be confirmed |
| 7 | new_order | Pipa PVC 3 inch × 12 batang; lem pipa × 6 (setengah lusin); **pickup**, not delivery; 14:00; name Yanto | Numbers in words. No date given: null or today, but never another date |
| 8 | new_order | Seng gelombang 0.3 × 10 lembar; paku 5 cm × 3 kg; kawat duri × 1 roll; delivery to Jl. Sukajadi 88; date 2026-11-19 (Thursday), around midday; payment: COD; agreed total Rp 1.250.000 in notes | The price was agreed in an earlier chat. Record it, but flag it for the admin to check |
| 9 | new_order | Plywood 9 mm × 2 lembar; lem kayu × 1 kaleng; delivery to Dago, date 2026-11-18 (today); name Kevin | Written in English. "Dago" is an area, not a full address |
| 10 | new_order | Besi beton × 1 ikat, size unknown; delivery address unknown | Almost everything is "the usual". The right output is mostly nulls plus questions: which size, which address, who is this |

## Scoring yourself

For each message, count it as correct only if every fact in "Must contain" is
right **and** nothing was invented. Write the score down (for example 7/10),
then try to raise it by changing only the system prompt. That's prompt
engineering, and writing down a score is your first, hand-made eval.
