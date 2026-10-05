# Step 4 — Cleaning

## What was done
Ran on both Step 3 outputs (`primary_dataset.csv`, `urgency_dataset.csv`). Code:
`code/clean_datasets.py`. Full run log: `output/clean_log.txt`.

For each row:
1. Dropped `[removed]`/`[deleted]` junk markers (re-checked post-Step-3; found 0 in
   both, consistent with Step 2's original EDA).
2. Fixed unicode/mojibake artifacts (`ftfy`) — e.g. curly-quote encoding issues.
3. Stripped URLs, Reddit `u/username` and `r/subreddit` references, Twitter-style
   `@mentions`, email addresses, and phone-number-like patterns.
4. Converted emojis to text descriptions instead of deleting them (`emoji.demojize`)
   — e.g. 😊 → "smiling face with smiling eyes" — since emoji carry real emotional
   signal for this task, per the Phase 1 plan.
5. Dropped rows that became empty after the above (i.e. a post that was *only* a URL
   or emoji).
6. Dropped duplicate rows *created by cleaning* (e.g. two posts that only differed by
   which URL they linked to are now identical text).
7. Flagged (not dropped) rows a lightweight heuristic thinks are likely non-English —
   see Limitation below.

## Results (after the glued-text fix below; see revision note)

| | rows in | junk dropped | empty-after-clean dropped | new dupes dropped | rows out |
|---|---|---|---|---|---|
| primary_dataset | 51,073 | 0 | 1 | 17 | **51,055** |
| urgency_dataset | 232,074 | 0 | 6 | 125 | **231,943** |

Class balance barely moved (e.g. primary: Normal 16,039 → 16,031, Suicidal 10,641 →
10,638) — cleaning removed noise, not signal.

`likely_non_english` flag: 4.27% of primary_dataset, 0.85% of urgency_dataset. Kept
as a column rather than dropped rows outright — see Limitation below.

## Revision: glued title/body text (found in Step 6, fixed here)
Step 6's word-frequency analysis surfaced a real upstream data bug: many posts have
their title and body concatenated with **zero separator** — e.g. the raw text
`"i dont want to live anymoreI'm having a hard time because..."` is actually the
title *"I don't want to live anymore"* stuck directly onto the body *"I'm having a
hard time..."* with no space or newline between them. This was confirmed in the
original raw files, not introduced by this pipeline:

- `Combined Data.csv`: 2,563 rows affected (4.8%)
- `Suicide_Detection.csv`: 66,271 rows affected (**28.6%** — nearly a third)

Fixed with one added regex step in `clean_text()`: insert a space wherever a
lowercase/digit character is immediately followed by an uppercase character
(`(?<=[a-z0-9])(?=[A-Z])` → space). Verified this doesn't damage genuine acronyms
(`PTSD`, `ADHD` stay intact since they're all-uppercase runs); the rare false-positive
cost is something like `iPhone` → `i Phone`, an acceptable tradeoff for this domain.
This step was re-run in full after adding the fix — the Results table above already
reflects the corrected numbers. Step 5 and Step 6 were re-run downstream of this fix.

## Spot-check (before → after)
```
BEFORE: my playlist is a mess. pls röäšt me https://open.spotify.com/playlist/...
AFTER:  my playlist is a mess. pls röäšt me

BEFORE: Feel free to DM me 😊
AFTER:  Feel free to DM me :smiling face with smiling eyes:

BEFORE: I'm leaving r/teenagers, it's been a good one!
AFTER:  I'm leaving , it's been a good one!
```

## Limitation: no compiled language-detection library available
`langdetect` (and a couple of alternatives) failed to install in this sandbox —
their `setup.py` build is incompatible with the environment's `setuptools` version,
and no working substitute with a prebuilt wheel was found. Rather than block on it,
the same lightweight heuristic from Step 2 (share of common-English-stopword hits in
the text) is used to **flag** likely non-English/degenerate rows as a new
`likely_non_english` column, without dropping them. This keeps the decision visible
and reversible: Step 6 (EDA on cleaned data) should manually spot-check a sample of
flagged rows before deciding whether to actually drop them or not. If a real
language-ID library becomes installable later (e.g. on the machine actually running
training), swapping it in is a one-line change to `clean_text()`.

## PII handling — what's covered and what isn't
Emails and phone-number-like patterns are stripped by regex. Usernames/handles are
stripped where platform-structured (`u/`, `r/`, `@handle`). What is **not** covered:
a third party's real name mentioned in free text (e.g. "my friend Sarah told me...").
Proper removal of that needs a named-entity-recognition pass, which is a candidate
for a follow-up pass in Step 5/6 rather than blocking Step 4 — flagging this
explicitly rather than silently claiming full PII removal.

## Output files
`output/primary_dataset_clean_{train,val,test}.csv.gz` and
`output/urgency_dataset_clean_{train,val,test[,_partN]}.csv.gz` — same gzip/chunking
convention as Step 3 (see root `PIPELINE_README.md`).
