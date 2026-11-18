---
name: skill-copies
description: Audit a skill collection for platform-copy divergence. Clusters physical skill packages into logical skills by name, aligns the platform copies of each skill, and classifies them as identical, frontmatter-only divergence, or body divergence with a similarity score. Use when maintaining or installing from a collection that ships the same skill for multiple agent platforms.
---

# skill-copies

Skill collections increasingly ship the same logical skill as several
platform copies (for example under `skills/`, `.agents/skills/`,
`.cursor/skills/`, `.kiro/skills/`, `pi/core/skills/`). The copies are
supposed to be mirrors. This skill checks whether they actually are.

## What it does

1. Walks a collection root and finds every `SKILL.md` outside any `docs/`
   directory (locale editions are out of scope for this skill).
2. Groups packages into logical skills by their frontmatter `name`.
3. For each group with two or more copies, classifies the group:
   - `identical` — frontmatter and body hashes all equal;
   - `frontmatter_only` — bodies equal, frontmatter differs (format
     adaptation across platforms);
   - `body_diverged` — bodies differ; reports the minimum pairwise body
     similarity (whitespace-normalized, difflib ratio).
4. Prints a summary (physical packages, logical skills, multi-copy
   groups, class counts) and optionally writes the full per-group
   report as JSON.

## Invocation

```bash
python3 scripts/audit_copies.py <collection_root> [report.json]
```

## Requirements

- Python 3.10+ standard library only. No network, no model calls.
- Deterministic: the same collection always produces the same report.

## Output

Summary JSON on stdout; with the optional second argument, a full
report (`summary` + per-group `groups`) written to that path.
