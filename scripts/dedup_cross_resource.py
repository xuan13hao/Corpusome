#!/usr/bin/env python3
"""
dedup_cross_resource.py — detect samples present in more than one source resource,
by matching ENA/SRA run, sample (ERS/SRS) and BioSample (SAMEA/SAMN) accessions
parsed from the sample identifiers.

Result (v1.2): 0 accessions shared between sources -> 0 cross-resource duplicates.
Coverage is partial: AGP carries Qiita ids (no ENA accession), the MGnify full pull
is keyed by run accessions while the selective MGnify pull and cMD carry sample/
BioSample accessions, so cross-accession-level matches cannot be resolved from ids.

Writes documents/cross_resource_duplicates.csv (empty if none).
"""
import os, re
import pandas as pd
from collections import defaultdict, Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cat = pd.read_parquet(os.path.join(REPO, "data/metadata/corpus_metadata_catalog_expanded.parquet"))
cat["uid"] = cat.sample_uid.astype(str)

PAT = re.compile(r"(ERR\d+|SRR\d+|DRR\d+|ERS\d+|SRS\d+|DRS\d+|SAMEA\d+|SAMN\d+|SAMD\d+)")

acc2src, acc2uid = defaultdict(set), defaultdict(list)
for r in cat.itertuples():
    for a in set(PAT.findall(r.uid)):
        acc2src[a].add(r.source); acc2uid[a].append((r.source, r.uid))

cross = {a: s for a, s in acc2src.items() if len(s) > 1}
print("cross-resource duplicate accessions:", len(cross))

rows = []
for a, srcs in cross.items():
    for src, uid in acc2uid[a]:
        rows.append({"accession": a, "source": src, "sample_uid": uid})
dup = pd.DataFrame(rows, columns=["accession", "source", "sample_uid"])
out = os.path.join(REPO, "documents", "cross_resource_duplicates.csv")
dup.to_csv(out, index=False)
print(f"wrote {os.path.relpath(out, REPO)} ({len(dup)} rows)")

# accession-type coverage per source (for the Methods caveat)
def kinds(u):
    k = set()
    for pat, name in [(r"ERR\d+|SRR\d+|DRR\d+", "run"), (r"ERS\d+|SRS\d+|DRS\d+", "sample"),
                      (r"SAMEA\d+|SAMN\d+|SAMD\d+", "biosample")]:
        if re.search(pat, u): k.add(name)
    return tuple(sorted(k)) or ("none",)
print("\naccession-type coverage per source:")
for s in cat.source.unique():
    print(f"  {s}: {dict(Counter(kinds(u) for u in cat.loc[cat.source==s,'uid']))}")
