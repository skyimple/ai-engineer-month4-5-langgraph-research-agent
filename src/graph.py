"""LangGraph workflow for the research agent."""

from langgraph.graph import StateGraph, START, END

from src.state import ResearchState
from src.nodes import planner_node, researcher_node, writer_node, saver_node


# Build the linear workflow graph
workflow = StateGraph(ResearchState)

workflow.add_node("planner", planner_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)
workflow.add_node("saver", saver_node)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", "saver")
workflow.add_edge("saver", END)

graph = workflow.compile()
