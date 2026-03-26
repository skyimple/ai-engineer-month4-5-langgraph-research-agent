# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research agent using LangGraph's StateGraph for workflow orchestration with human-in-the-loop. Uses Alibaba Cloud DashScope's Qwen3.5-plus model via OpenAI-compatible API. Supports LangSmith tracing, Phoenix observability, A/B testing, and Guardrails security.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the LangGraph research agent
python -m src.main "AI"

# Run A/B comparison test
python ab_test.py "AI"

# Run evaluation system
python evals/runners/daily_eval.py
python evals/runners/daily_eval.py --limit 5  # limit topics

# Legacy ReAct agent
python simple_react.py
```

## Architecture

**Core LangGraph Workflow** (linear pipeline with interrupts):
```
planner → [interrupt] → researcher → writer → [interrupt] → saver
```

**Key Files:**
- `src/main.py` - CLI entry point with human-in-the-loop interaction
- `src/graph.py` - StateGraph definition with `interrupt_before=["researcher", "saver"]`
- `src/nodes.py` - 4 nodes: planner, researcher, writer, saver (all `@traceable`)
- `src/state.py` - ResearchState TypedDict
- `src/config.py` - LLM config, LangSmith, Phoenix, A/B testing configuration
- `src/guardrails/rails.py` - Input/output security checks

**Production Components:**
- `evals/` - Evaluation system (metrics, datasets, runners)
- `ab_test.py` - A/B testing framework for comparing model versions
- `.github/workflows/daily_eval.yml` - GitHub Actions scheduled evaluation

## API Configuration

Environment variables from `config.env`:
- `DASHSCOPE_API_KEY` - Alibaba Cloud DashScope API key (required)
- `LANGSMITH_API_KEY` - LangSmith tracing (optional)
- `LANGSMITH_PROJECT` - LangSmith project name (default: "research-agent")
- `AB_TEST_PROMPT_VERSION` - A/B version: "A" or "B"
- `AB_TEST_MODEL_A` / `AB_TEST_MODEL_B` - Model names for A/B testing

DuckDuckGo is used for web search (no API key required).

## Human-in-the-Loop

The agent pauses at `researcher` and `saver` nodes for human review:

```python
graph = workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["researcher", "saver"]
)
```

User interactions at interrupt points:
- `approve` - continue to next step
- `modify: <instruction>` - re-run node with modification

## Production Features

**Observability:** LangSmith tracing with `@traceable(metadata={"node": "planner"})` on all nodes. Phoenix integration via `ARIZE_PHOENIX_API_KEY` environment variable.

**Evaluation:** `evals/runners/daily_eval.py` calculates faithfulness, relevance, and source_accuracy metrics against 30 test topics in `evals/datasets/topics.json`.

**A/B Testing:** `ab_test.py` runs the same topic through versions A and B, comparing latency, token usage, and output quality. Reports saved to `evals/reports/`.

**Security:** `src/guardrails/rails.py` checks user input and agent output for dangerous patterns (SQL injection, code execution, XSS). Logs written to `logs/guardrails_logs/`.

## Notes

- System prompts and CLI are in Chinese
- Reports saved to `outputs/{topic}_report.md`
- `calculator_tool` in `tools.py` validates input before `eval()` for security
- `simple_react.py` is legacy pre-LangGraph implementation
