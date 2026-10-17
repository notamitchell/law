# Review of the grammatical abbreviations (October 2026)

The two scripts that applied the review recorded in the doc "Grammatical abbreviations: queries" (claude.ai artifact 40bc6fd8-17a2-4410-a12e-4226aa674c8e). They are kept as a record of every change; they were run once and should not be run again (they expect the files as they were before the review).

- `apply-list.py`: the changes to `data/markforward.json` (layout split into Liebermann's form and "Modern German", corrected definitions, new and removed rows, renamed anchors).
- `apply-entries.py`: the matching link changes in `entries/` (relinked, unlinked and newly linked abbreviations), with each decision listed by entry.
- `renames.json`: anchors renamed, old → new.
- Done by hand after the scripts: the row for *vor.* (vorig), the apostrophes in the notes (‘s → ’s) and the note on the *Objekt* row.
