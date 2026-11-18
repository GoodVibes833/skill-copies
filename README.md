# Artifact — skill-copies

Verifiable skill artifact accompanying the submission on platform-copy
divergence in public skill collections.

## Contents

- `skill-copies/SKILL.md` — the skill (installable as-is in any host
  that loads SKILL.md-based skills).
- `skill-copies/scripts/audit_copies.py` — the deterministic audit
  script the skill invokes.
- `reproduction.json` — the report produced by the run below.

## Environment requirements

- Python 3.10 or newer (standard library only; nothing to install).
- A checkout of the public collection studied in the paper
  (Everything Claude Code / ECC), or any collection laid out the
  same way.

## Reproduction

```bash
python3 skill-copies/scripts/audit_copies.py <collection_root> report.json
```

Expected summary on the studied collection:

```json
{
  "physical_packages": 550,
  "logical_skills": 316,
  "multi_copy_groups": 161,
  "class_counts": {"identical": 90, "frontmatter_only": 23, "body_diverged": 48},
  "platform_pairs_vs_canonical": {".agents": "22/46", ".cursor": "7/12", ".kiro": "31/43", "pi": "0/133"}
}
```

The studied snapshot is pinned to ECC commit
`d2ef2680594f9a17526a6e1a2e18b3d242c5d17b` (v2.2.3);
`snapshot-manifest.txt` lists the SHA-256 of every studied file.

The full per-group classification is in `report.json` (`groups`).
