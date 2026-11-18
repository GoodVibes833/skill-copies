#!/usr/bin/env python3
"""audit_copies.py — cluster platform copies of each logical skill in a
collection and classify their divergence.
Usage: python3 audit_copies.py <collection_root> [out.json]
Excludes any path under a docs/ directory (locale editions are out of scope).
Also reports, for each platform tree, how many of its skills that also
appear in the canonical skills/ tree have a body differing from the
canonical copy (platform pairs), the similarity bands of diverged groups,
and — for frontmatter-only groups — which frontmatter fields diverge.
Grouping uses the frontmatter `name:` value with any surrounding single
or double quotes stripped (a quoted name denotes the same logical skill);
packages whose SKILL.md has no usable name field are counted in the
summary as `packages_without_name` instead of being dropped silently,
and the run fails if no named package is found at all.
Deterministic: traversal and copies are processed in sorted path order,
and body similarity is a canonical-direction difflib ratio with autojunk
disabled, so re-runs on the same collection are byte-stable.
Python standard library only.
"""
import os, re, sys, json, hashlib, difflib
from collections import defaultdict, Counter

def split(t):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", t, re.S)
    return (m.group(1), m.group(2)) if m else ("", t)

def name_of(fm):
    mm = re.search(r"^name:\s*(.+)$", fm, re.M)
    if not mm:
        return None
    n = mm.group(1).strip()
    if len(n) >= 2 and n[0] == n[-1] and n[0] in "\"'":
        n = n[1:-1].strip()
    return n.lower() or None

def platform_of(rel):
    parts = rel.split("/")
    return parts[0] if len(parts) > 1 else "(root)"

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def fm_fields(fm):
    """Top-level frontmatter fields: key -> raw block text (the key line
    plus any indented continuation lines)."""
    fields = {}
    cur = None
    for line in fm.split("\n"):
        m = re.match(r"^([A-Za-z0-9_-]+):", line)
        if m:
            cur = m.group(1)
            fields[cur] = [line]
        elif cur is not None:
            fields[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in fields.items()}

def similarity(a, b):
    """Canonical body similarity of two whitespace-normalized bodies:
    difflib ratio with autojunk disabled, always computed in the same
    argument direction (shorter string first, ties broken
    lexicographically), so the value does not depend on copy order."""
    if (len(a), a) <= (len(b), b):
        x, y = a, b
    else:
        x, y = b, a
    return difflib.SequenceMatcher(None, x, y, autojunk=False).ratio()

def main(argv):
    if len(argv) < 2:
        print("usage: python3 audit_copies.py <collection_root> [out.json]",
              file=sys.stderr)
        return 2
    root = argv[1]
    if not os.path.isdir(root):
        print(f"error: collection root is not a directory: {root}",
              file=sys.stderr)
        return 1
    by_name = defaultdict(list)
    unnamed = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git"))
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
                    "body_h": hashlib.sha256(body.encode()).hexdigest(),
                    "fm": fm, "body": body})
            else:
                unnamed += 1
    if not by_name:
        print(f"error: no skill packages (SKILL.md with a frontmatter name) "
              f"found under {root} ({unnamed} SKILL.md package(s) had no "
              f"usable name field)", file=sys.stderr)
        return 1
    for v in by_name.values():
        v.sort(key=lambda x: x["path"])
    groups = []
    pairs = defaultdict(lambda: [0, 0])
    bands = Counter()
    fm_div = Counter()
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
        if cls == "frontmatter_only":
            per_copy = [fm_fields(x["fm"]) for x in v]
            keys = set()
            for f in per_copy:
                keys.update(f)
            for k in sorted(keys):
                if len({f.get(k) for f in per_copy}) > 1:
                    fm_div[k] += 1
        min_sim = None
        if cls == "body_diverged":
            bs = [norm(x["body"]) for x in v]; min_sim = 1.0
            for i in range(len(bs)):
                for j in range(i + 1, len(bs)):
                    min_sim = min(min_sim, similarity(bs[i], bs[j]))
            min_sim = round(min_sim, 3)
            bands["<0.5" if min_sim < 0.5 else "0.5-0.9" if min_sim < 0.9 else
                  "0.9-0.99" if min_sim < 0.99 else ">=0.99"] += 1
        groups.append({"name": n, "copies": len(v),
                       "platforms": sorted({x["platform"] for x in v}),
                       "class": cls, "min_body_similarity": min_sim})
    summary = {"physical_packages": sum(len(v) for v in by_name.values()),
               "packages_without_name": unnamed,
               "logical_skills": len(by_name), "multi_copy_groups": len(groups),
               "class_counts": dict(Counter(g["class"] for g in groups)),
               "frontmatter_only_field_divergence":
                   dict(sorted(fm_div.items(), key=lambda kv: (-kv[1], kv[0]))),
               "platform_pairs_vs_canonical": {k: f"{a}/{b}" for k, (a, b) in sorted(pairs.items())},
               "diverged_similarity_bands": dict(bands)}
    out = {"summary": summary, "groups": groups}
    print(json.dumps(summary, indent=1))
    if len(argv) > 2:
        json.dump(out, open(argv[2], "w"), indent=1)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
