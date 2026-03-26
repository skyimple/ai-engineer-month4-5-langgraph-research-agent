# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research agent that uses LangGraph's StateGraph for workflow orchestration. The agent performs web search and generates research reports. It uses Alibaba Cloud DashScope's Qwen3.5-plus model via OpenAI-compatible API.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the LangGraph research agent (topic from argument or interactive input)
python -m src.main "AI"

# Run the interactive ReAct agent (legacy manual loop)
python simple_react.py

# Run tests in Jupyter notebook
jupyter notebook test.ipynb
```

## Architecture

```
src/
  main.py                # CLI entry point for LangGraph agent
  graph.py               # LangGraph StateGraph workflow definition
  nodes.py                # Agent nodes: planner, researcher, writer, saver
  state.py               # ResearchState TypedDict
  config.py              # LLM configuration (DashScope API, Qwen3.5-plus)
  tools.py               # Tools: search_tool, calculator_tool, save_markdown_tool
simple_react.py          # Legacy ReAct agent with manual while-loop
```

**LangGraph Workflow** (linear pipeline):
1. `planner_node` - Generates research steps using LLM + search tool
2. `researcher_node` - Executes searches for each step, collects sources
3. `writer_node` - Generates Markdown report using collected information
4. `saver_node` - Saves report to `outputs/` directory

**ResearchState** (TypedDict):
- `topic`: Research topic
- `messages`: Conversation history (Annotated with add_messages)
- `research_steps`: List of planned search queries
- `sources`: List of dicts with title, url, snippet
- `report_draft`: Generated Markdown content
- `final_markdown_path`: Output file path

## API Configuration

Environment variables loaded from `config.env`:
- `DASHSCOPE_API_KEY` - Alibaba Cloud DashScope API key for Qwen3.5-plus model (required)
- DuckDuckGo is used for web search (no API key required, uses `duckduckgo-search` package)

## Human-in-the-Loop Architecture

The agent uses LangGraph's `interrupt_before` to pause at key nodes for human review:

```python
graph = workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["researcher", "saver"]  # Interrupt before these nodes
)
```

**Workflow with interrupts:**
1. `planner` → interrupt → user approves/modifies research plan
2. `researcher` → executes searches
3. `writer` → interrupt → user approves/modifies report draft
4. `saver` → saves to `outputs/`

User interactions:
- `approve` - continue to next step
- `modify: <instruction>` - re-run node with modification instruction

**State persistence:** `MemorySaver` checkpointer maintains execution state, allowing resumption after interrupts via `Command(resume="continue")`.

## Key Dependencies

- **langgraph** - Workflow orchestration with checkpointing and interrupts
- **langchain-openai** - LLM interface (DashScope compatible)
- **duckduckgo-search** - Web search tool
- **python-dotenv** - Environment variable loading

## Notes

- System prompts and CLI are in Chinese
- `src/main.py` accepts topic as CLI argument: `python -m src.main "AI"`
- Reports are saved to `outputs/{topic}_report.md`
- `calculator_tool` validates input characters before eval() for security
- `simple_react.py` is a legacy ReAct agent with manual while-loop (pre-LangGraph)
- `src/__init__.py` exists but is empty (package marker only)
