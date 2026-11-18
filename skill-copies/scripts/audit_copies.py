#!/usr/bin/env python3
"""audit_copies.py — cluster platform copies of each logical skill in a
collection and classify their divergence.
Usage: python3 audit_copies.py <collection_root> [out.json]
Excludes any path under a docs/ directory (locale editions are out of scope).
Also reports, for each platform tree, how many of its skills that also
appear in the canonical skills/ tree have a body differing from the
canonical copy (platform pairs), and the similarity bands of diverged
groups. Deterministic; Python standard library only.
"""
import os, re, sys, json, hashlib, difflib
from collections import defaultdict, Counter

def split(t):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", t, re.S)
    return (m.group(1), m.group(2)) if m else ("", t)

def name_of(fm):
    mm = re.search(r"^name:\s*(.+)$", fm, re.M)
    return mm.group(1).strip().lower() if mm else None

def platform_of(rel):
    parts = rel.split("/")
    return parts[0] if len(parts) > 1 else "(root)"

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def main():
    root = sys.argv[1]
    by_name = defaultdict(list)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        if "SKILL.md" in files:
            rel = os.path.relpath(dirpath, root)
            if rel.startswith("docs/") or "/docs/" in rel:
                continue
            t = open(os.path.join(dirpath, "SKILL.md"), encoding="utf-8", errors="ignore").read()
            fm, body = split(t)
            n = name_of(fm)
            if n:
                by_name[n].append({"path": rel, "platform": platform_of(rel),
                    "fm_h": hashlib.sha256(fm.encode()).hexdigest(),
                    "body_h": hashlib.sha256(body.encode()).hexdigest(), "body": body})
    groups = []
    pairs = defaultdict(lambda: [0, 0])
    bands = Counter()
    for n, v in sorted(by_name.items()):
        canon = [x for x in v if x["platform"] == "skills"]
        if canon:
            c = canon[0]
            for x in v:
                if x["platform"] == "skills":
                    continue
                pairs[x["platform"]][1] += 1
                if x["body_h"] != c["body_h"]:
                    pairs[x["platform"]][0] += 1
        if len(v) < 2:
            continue
        fms = {x["fm_h"] for x in v}; bodies = {x["body_h"] for x in v}
        if len(bodies) == 1 and len(fms) == 1: cls = "identical"
        elif len(bodies) == 1: cls = "frontmatter_only"
        else: cls = "body_diverged"
        min_sim = None
        if cls == "body_diverged":
            bs = [norm(x["body"]) for x in v]; min_sim = 1.0
            for i in range(len(bs)):
                for j in range(i + 1, len(bs)):
                    min_sim = min(min_sim, difflib.SequenceMatcher(None, bs[i], bs[j]).ratio())
            min_sim = round(min_sim, 3)
            bands["<0.5" if min_sim < 0.5 else "0.5-0.9" if min_sim < 0.9 else
                  "0.9-0.99" if min_sim < 0.99 else ">=0.99"] += 1
        groups.append({"name": n, "copies": len(v),
                       "platforms": sorted({x["platform"] for x in v}),
                       "class": cls, "min_body_similarity": min_sim})
    summary = {"physical_packages": sum(len(v) for v in by_name.values()),
               "logical_skills": len(by_name), "multi_copy_groups": len(groups),
               "class_counts": dict(Counter(g["class"] for g in groups)),
               "platform_pairs_vs_canonical": {k: f"{a}/{b}" for k, (a, b) in sorted(pairs.items())},
               "diverged_similarity_bands": dict(bands)}
    out = {"summary": summary, "groups": groups}
    print(json.dumps(summary, indent=1))
    if len(sys.argv) > 2:
        json.dump(out, open(sys.argv[2], "w"), indent=1)

if __name__ == "__main__":
    main()
