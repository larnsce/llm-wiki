# Verdict rubric and verification-subagent protocol

Spec: openspec/specs/audit.md REQ-922..923; openspec/specs/citations.md
REQ-901..903

## The verdict set (closed; REQ-923)

| Verdict | Meaning |
|---|---|
| `supported` | The source states the claim's fact (same substance; wording may differ). Numbers, dates, and directions match. |
| `partial` | The source supports part of the claim but not all of it, supports it only with material hedging the claim drops, or supports a weaker version (e.g. claim says "24%", source says "over 20%"). |
| `unsupported` | The source does not state the fact, or states something that contradicts it. A contradiction is `unsupported` with the contradiction named in the justification. |
| `source-missing` | The cite target does not resolve: the `ingested/` path is not on disk, or the `url:` ref cannot be fetched. No judgment on the claim is possible or attempted. |

Rules:

- The verdict answers ONE question: does THIS source support THIS claim. Not
  whether the claim is true, well-written, or supported elsewhere.
- Justification is one line, paraphrased, no long quotes (REQ-923). Name the
  locator region checked when the ref carries one (`#p12`, `#sec-3.2`;
  citations.md REQ-901). A locator is free text and advisory: if the fact sits
  elsewhere in the source, the claim is still `supported`; note the actual
  location.
- A claim with multiple refs (citations.md REQ-901) gets one verdict PER
  source, each from that source's own subagent. Reconciliation (Phase 3)
  combines them; the subagents never see each other's verdicts.

## Isolation rules (REQ-922)

Each verification subagent receives EXACTLY:

1. the claim text(s) citing its source, verbatim, with block locations;
2. its one source: the `ingested/` file content read from disk, or the fetched
   content of the `url:` ref;
3. the rubric above.

It receives NOTHING else: not the page, not the page's properties, not the
other claims, not the other sources, and no verdict from any other subagent.
Cross-contamination would let a well-supported neighbor claim launder an
unsupported one.

## Subagent prompt template

```
You are verifying claims against ONE source. Judge ONLY whether this source
supports each claim; do not judge whether a claim is true in general.

Source (<ref>):
<full source text>

Claims citing this source:
1. "<claim text>" (block: <location>, locator: <#locator or none>)
2. ...

For each claim return exactly:
- verdict: supported | partial | unsupported
- justification: one line, paraphrased, no long quotes; name where in the
  source you looked.
```

`source-missing` is assigned by the orchestrator when the target does not
resolve; such a source gets no subagent.

## Dispatch

- One subagent per cited SOURCE, not per claim (REQ-922): a source cited by
  three claims gets one subagent judging all three.
- Dispatch all subagents in parallel (a single message with one Task tool call
  per source).
- Same underlying work exported twice (citations.md REQ-903) still means two
  subagents here; the ONE-source de-duplication applies to corroboration
  counting in reconciliation, not to verification dispatch.
