"""LangGraph agent for freelance job reporting.

Interfaces:
  - graph.invoke({"query": ..., "max_jobs": ...}) -> {"report_md", "all_jobs", ...}
    Deterministic pipeline: fetch jobs -> LLM writes the report. Used by
    agent/run.py. One LLM call -> fast and reliable on slow CPUs.
  - build_agent() -> ReAct tool agent (fetch_upwork / save_report tools) for
    learning the multi-turn tool-loop pattern.
"""
import json
import os
import time
from datetime import date
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

from scrapers.freelancer import fetch_freelancer_jobs
from scrapers.upwork import UpworkBlockedError, fetch_upwork_jobs


class AgentState(TypedDict):
    query: str
    max_jobs: int
    all_jobs: list
    report_md: str


REPORT_SYSTEM_PROMPT = """You are a freelance job intelligence assistant.

You are given a JSON list of freelance job postings. Your task:
1. Keep only AI/ML, machine learning, AI agent, LLM, RAG, automation, or
   similar roles. Drop clearly irrelevant ones (e.g. pure logo design).
2. Rank the kept jobs by relevance first, then by budget size.
3. Write a complete markdown report:
   - A title line and the generation date (use the exact date the user provides).
   - A 1-2 line summary: how many jobs found vs kept.
   - List EVERY kept job, each with: title (as a link), budget, type, posted
     date, and a short description (keep under 2 lines).
4. Return ONLY the markdown report. No extra commentary, no code fences.
"""


def _model():
    return ChatOllama(
        model=os.environ.get("OLLAMA_MODEL", "phi4-mini"),
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
        num_ctx=3072,
        num_predict=700,
        model_kwargs={"think": False},
    )


def _fetch_jobs_node(state: AgentState) -> dict:
    source = os.environ.get("FREELANCE_SOURCE", "auto")
    if source == "freelancer":
        jobs = fetch_freelancer_jobs(state["query"], state["max_jobs"])
    else:
        try:
            jobs = fetch_upwork_jobs(state["query"], state["max_jobs"])
        except UpworkBlockedError:
            jobs = fetch_freelancer_jobs(state["query"], state["max_jobs"])
    print(f"  [fetch] got {len(jobs)} jobs", flush=True)
    return {"all_jobs": jobs}


def _generate_report_node(state: AgentState) -> dict:
    jobs_json = json.dumps(state["all_jobs"], indent=2)[:8000]
    llm = _model()
    messages = [
        SystemMessage(content=REPORT_SYSTEM_PROMPT),
        HumanMessage(content=f"Today's date: {date.today().isoformat()}\n\nJobs JSON:\n{jobs_json}"),
    ]
    print(f"  [report] generating with {len(state['all_jobs'])} jobs...", flush=True)
    resp = None
    for attempt in range(3):
        try:
            resp = llm.invoke(messages)
            break
        except Exception as e:  # noqa: BLE001 - retry dropped connections
            print(f"  [report] attempt {attempt + 1} failed ({type(e).__name__}), retrying...", flush=True)
            time.sleep(2)
    if resp is None:
        raise RuntimeError("report generation failed after 3 attempts")
    print("  [report] done", flush=True)
    return {"report_md": (resp.content or "").strip()}


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("fetch", _fetch_jobs_node)
    g.add_node("report", _generate_report_node)
    g.set_entry_point("fetch")
    g.add_edge("fetch", "report")
    g.add_edge("report", END)
    return g.compile()


graph = _build_graph()
