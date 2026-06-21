"""
MeetIQ Evaluation Pipeline
===========================

Runs the full research agent against fixture companies and scores the output.

Scoring dimensions (each 0–10):
  relevance      — Is information useful for a pre-meeting context?
  specificity    — Are claims specific (named products, dates) vs vague ("growing fast")?
  recency        — Is news actually from the last 90 days, not older history?
  actionability  — Are talking points specific and non-generic conversation starters?

Overall score = average of all 4 dimensions.

Run with:
    PYTHONPATH=src python evals/run_evals.py

Results saved to: evals/results/eval_<timestamp>.json
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime

# Add the src directory to path so meetiq imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage

from meetiq.config.settings import settings
from meetiq.core.logging import logger
from meetiq.models.brief import ResearchBrief
from meetiq.services.research_service import research_company

# ── Scoring rubric sent to Gemini-as-judge ─────────────────────────────────────

JUDGE_PROMPT = """You are evaluating the quality of a pre-meeting intelligence brief for a sales call.

Company: {company_name}
Brief produced:
{brief_json}

Score this brief on exactly 4 dimensions, each from 0 to 10:

1. relevance (0-10)
   - 10: All information directly useful for a sales call — what they do, current priorities, why they'd buy
   - 5: Mix of useful and generic/off-topic information
   - 0: Information not useful for sales context at all

2. specificity (0-10)
   - 10: Named products, specific features, exact technologies, concrete examples
   - 5: Some specific claims mixed with vague statements
   - 0: Entirely vague ("they are growing", "innovative company")

3. recency (0-10)
   - 10: News items are clearly from last 90 days with dates or recent context
   - 5: Mix of recent and older news, or dates unclear
   - 0: All news is old (pre-2024) or recent_news is empty

4. actionability (0-10)
   - 10: Talking points are specific, non-generic questions tied to this company's situation
   - 5: Some specific, some generic ("tell me about your challenges")
   - 0: All generic talking points that could apply to any company

Also flag any hallucinations you notice: specific numbers (revenue, headcount, valuations)
that seem invented rather than sourced from real public data.

Return ONLY valid JSON with this exact structure:
{{
  "scores": {{
    "relevance": <number>,
    "specificity": <number>,
    "recency": <number>,
    "actionability": <number>
  }},
  "total": <average of all 4>,
  "hallucination_flags": ["description of any hallucinated claim", ...],
  "judge_notes": "brief explanation of the scores in 2-3 sentences"
}}"""

# ── Judge LLM (same Gemini model, but acting as evaluator) ────────────────────

_judge_llm = ChatBedrockConverse(
    model=settings.bedrock_model,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
    temperature=0.0,   # Zero temp — we want consistent, deterministic scores
)


async def score_brief(company_name: str, brief: ResearchBrief) -> dict:
    """
    Ask Gemini to evaluate the brief on 4 dimensions.

    Why LLM-as-judge:
    - Human-written rubrics can't capture nuance ("is this talking point actually good?")
    - Gemini can read the brief holistically and reason about quality
    - It's the same approach used by OpenAI Evals, Anthropic's Claude eval harness

    Limitation: same model that generated the brief is judging it — it may be
    overgenerous. In production you'd use a different/stronger model as judge.
    """
    brief_json = json.dumps(brief.model_dump(), indent=2)
    prompt = JUDGE_PROMPT.format(
        company_name=company_name,
        brief_json=brief_json,
    )

    try:
        response = await _judge_llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        return result
    except json.JSONDecodeError as e:
        logger.error("judge_parse_error", error=str(e))
        return {
            "scores": {"relevance": 0, "specificity": 0, "recency": 0, "actionability": 0},
            "total": 0,
            "hallucination_flags": [],
            "judge_notes": "Scoring failed — JSON parse error",
        }
    except Exception as e:
        logger.error("judge_failed", error=str(e)[:100])
        return {
            "scores": {"relevance": 0, "specificity": 0, "recency": 0, "actionability": 0},
            "total": 0,
            "hallucination_flags": [],
            "judge_notes": f"Scoring failed: {str(e)[:80]}",
        }


async def eval_company(fixture: dict) -> dict:
    """
    Run full research + scoring for one company fixture.

    Returns a result dict with the brief, scores, pass/fail, and timing.
    """
    company_name = fixture["name"]
    domain = fixture["domain"]
    expected_min = fixture.get("expected_min_score", 6.0)

    print(f"\n{'='*60}")
    print(f"  Evaluating: {company_name} ({domain})")
    print(f"{'='*60}")

    start = datetime.now()

    # Step 1: Research
    print(f"  [1/2] Running research agent...")
    brief = await research_company(company_name, domain)

    research_duration = (datetime.now() - start).total_seconds()
    print(f"  Research done in {research_duration:.1f}s | partial={brief.partial}")
    print(f"  Sources used: {len(brief.sources_used)}")

    # Step 2: Score
    print(f"  [2/2] Scoring brief...")
    eval_result = await score_brief(company_name, brief)

    total_duration = (datetime.now() - start).total_seconds()

    scores = eval_result.get("scores", {})
    total_score = eval_result.get("total", 0)
    passed = total_score >= expected_min

    print(f"\n  SCORES:")
    print(f"    Relevance:     {scores.get('relevance', 0):.1f}/10")
    print(f"    Specificity:   {scores.get('specificity', 0):.1f}/10")
    print(f"    Recency:       {scores.get('recency', 0):.1f}/10")
    print(f"    Actionability: {scores.get('actionability', 0):.1f}/10")
    print(f"    ─────────────────────")
    print(f"    TOTAL:         {total_score:.1f}/10  {'✓ PASS' if passed else '✗ FAIL'} (min {expected_min})")

    flags = eval_result.get("hallucination_flags", [])
    if flags:
        print(f"\n  ⚠ Hallucination flags:")
        for flag in flags:
            print(f"    - {flag}")

    notes = eval_result.get("judge_notes", "")
    if notes:
        print(f"\n  Judge notes: {notes}")

    return {
        "company": company_name,
        "domain": domain,
        "scenario": fixture.get("scenario", "unknown"),
        "passed": passed,
        "expected_min_score": expected_min,
        "total_score": total_score,
        "scores": scores,
        "hallucination_flags": flags,
        "judge_notes": notes,
        "brief_partial": brief.partial,
        "sources_count": len(brief.sources_used),
        "research_duration_s": round(research_duration, 2),
        "total_duration_s": round(total_duration, 2),
        "brief_summary": {
            "description": brief.description[:100],
            "recent_news_count": len(brief.recent_news),
            "tech_signals_count": len(brief.tech_signals),
            "talking_points_count": len(brief.talking_points),
        },
    }


async def run_all_evals(fixtures: list[dict]) -> dict:
    """
    Run evals for all fixtures sequentially (not parallel — rate limits).
    Save results to evals/results/eval_<timestamp>.json
    """
    print("\nMeetIQ Evaluation Pipeline")
    print(f"Running {len(fixtures)} companies...")

    results = []
    for fixture in fixtures:
        result = await eval_company(fixture)
        results.append(result)
        # Brief pause between companies to respect rate limits
        await asyncio.sleep(5)

    # Summary
    passed = sum(1 for r in results if r["passed"])
    avg_score = sum(r["total_score"] for r in results) / len(results) if results else 0

    print(f"\n{'='*60}")
    print(f"  EVAL SUMMARY")
    print(f"{'='*60}")
    print(f"  Companies evaluated: {len(results)}")
    print(f"  Passed:              {passed}/{len(results)}")
    print(f"  Average score:       {avg_score:.2f}/10")
    print(f"  Hallucination flags: {sum(len(r['hallucination_flags']) for r in results)}")

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"eval_{timestamp}.json")

    report = {
        "run_at": datetime.now().isoformat(),
        "summary": {
            "total_companies": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "average_score": round(avg_score, 2),
            "total_hallucination_flags": sum(len(r["hallucination_flags"]) for r in results),
        },
        "results": results,
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Results saved to: {output_path}")
    return report


if __name__ == "__main__":
    # Load fixtures
    fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_companies.json")
    with open(fixtures_path) as f:
        fixtures = json.load(f)

    # Allow running a single company: python run_evals.py Linear
    if len(sys.argv) > 1:
        name_filter = sys.argv[1].lower()
        fixtures = [f for f in fixtures if f["name"].lower() == name_filter]
        if not fixtures:
            print(f"No fixture found for '{sys.argv[1]}'")
            sys.exit(1)

    asyncio.run(run_all_evals(fixtures))
