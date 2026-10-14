# Bosworth-Toller links

Scripts that match the Old English entries in `entries/` to entries in Bosworth-Toller's *Anglo-Saxon Dictionary* and add `<xr type="bosworthToller">` links (shown under "Other dictionaries" on each entry page). They need no packages beyond Python 3.

The data is not in this repository (84 MB). Download `bosworth_entries_export.csv` from [LINDAT](https://lindat.mff.cuni.cz/repository/items/da2f3c19-f5a9-48d2-bb8f-eb84a415f954) (CC BY 4.0). Its columns are `id`, `headword` and `body` (the entry as XML), separated by `;`.

1. **Read the CSV** into a pickle of rows:
   `python3 -c "import csv,pickle,sys; csv.field_size_limit(10**9); pickle.dump(list(csv.reader(open(sys.argv[1],encoding='utf-8',newline=''),delimiter=';'))[1:], open('rows.pkl','wb'))" bosworth_entries_export.csv`
2. **Match**: `python3 match.py rows.pkl ../../entries out.json`. Grades each entry *sure*, *likely*, *unsure* or *none*:
    - spelling, ignoring length marks, hyphens and ð/þ; then spelling variants (i/y/ie, double letters, -ian/-an); then without *ge-*; then Liebermann's inflected headwords (*healle*, dt) traced to the dictionary form (*heall*);
    - part of speech, from Liebermann's labels (adv, prp, op, ptt, dt …) against Bosworth-Toller's;
    - shared law codes: Bosworth-Toller cites Thorpe's *Ancient Laws* ("L. In. 23" for Ine 23);
    - Liebermann's own cross-references: *Hyne s. Ine* is matched to Ine;
    - Bosworth-Toller entries that are one word (*a-bútan* prep. and adv.; *Dene* and *Dæne*, "the Danes") are linked together, each with its Supplement entries. Entries that only point elsewhere ("v. …") are left out.
3. **Review page**: `python3 build.py out.json page-template.html bt-matches.html` makes the review page, published on claude.ai as *Bosworth-Toller Matches*. An editor's choices are saved in the page's database, in the collection `decisions` (one document per entry: `{"ids": [...]}`; an empty list means no link).
4. **Apply**: `python3 apply.py <folder with out.json and db/decisions/*.json> rows.pkl`, run from the repository root. Adds links for sure and likely matches and for every entry with a saved choice (which wins). It only adds links; removing one that is already in an entry is done by hand.
