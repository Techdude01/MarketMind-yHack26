"""K2 Think V2 Agentic System with LangGraph + Tavily.

This is a true ReAct (Reason + Act) agent that autonomously decides when to search
the web using Tavily. K2 acts as the "brain," making reasoning decisions about
when it needs external information.

For hackathon agentic track qualification.
"""

import re
import time
import logging
from typing import List, Optional

try:
    from langchain_tavily import TavilySearch as TavilySearchResults
    _TAVILY_NEW_API = True
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults  # type: ignore[no-redef]
    _TAVILY_NEW_API = False

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from openai import InternalServerError

from app.config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domains excluded from Tavily searches during market analysis.
# Polymarket / Manifold prices are circular — they reflect the market itself
# rather than independent information about the underlying event.
# ---------------------------------------------------------------------------
_POLYMARKET_EXCLUDED_DOMAINS: List[str] = [
    "polymarket.com",
    "manifold.markets",
    "metaculus.com",   # also a prediction market — avoid echo-chamber sources
    "kalshi.com",
    "predictit.org",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class K2AgentState:
    """Thin wrapper kept for type-hint backwards compat."""
    messages: list


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks emitted by K2's reasoning process.

    K2-Think-v2 wraps its internal chain-of-thought inside ``<think>`` tags.
    The block always appears before the final answer, so stripping it leaves
    only the actual response the user/pipeline should see.

    The regex uses DOTALL so ``\\n`` inside the block is matched, and is
    non-greedy so multiple consecutive blocks are each removed individually.
    """
    # Remove <think>...</think> (case-insensitive, multi-line)
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Also strip any orphaned closing tags if the block wasn't closed cleanly
    cleaned = re.sub(r"</think>", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def create_k2_agent(exclude_domains: Optional[List[str]] = None):
    """Create a K2 Think V2 ReAct agent with Tavily search capabilities.

    Args:
        exclude_domains: Additional domains to block in Tavily searches.
            ``_POLYMARKET_EXCLUDED_DOMAINS`` is always prepended.

    Returns:
        A compiled LangGraph agent executor that can autonomously decide
        when to search the web.

    NOTE: K2's non-streaming endpoint returns HTTP 503 "Server is busy".
    Setting streaming=True forces LangChain to use the streaming path, which
    is stable. LangGraph's create_react_agent handles chunk assembly internally.

    # ── Gemini drop-in replacement ────────────────────────────────────────
    # pip install langchain-google-genai
    # from langchain_google_genai import ChatGoogleGenerativeAI
    # llm = ChatGoogleGenerativeAI(
    #     model="gemini-2.0-flash",
    #     google_api_key=Config.GEMINI_API_KEY,
    #     temperature=0,
    # )
    # ──────────────────────────────────────────────────────────────────
    """
    if not Config.K2_THINK_V2_API_KEY:
        raise RuntimeError("K2_THINK_V2_API_KEY is not set in .env")
    if not Config.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not set in .env")

    # Initialize K2 Think V2 as a LangChain OpenAI-compatible LLM.
    # streaming=True is required — K2's non-streaming endpoint returns 503.
    llm = ChatOpenAI(
        model="MBZUAI-IFM/K2-Think-v2",
        api_key=Config.K2_THINK_V2_API_KEY,
        base_url=Config.K2_THINK_V2_BASE_URL,
        temperature=0,
        timeout=60.0,
        streaming=True,  # required — K2's non-streaming endpoint is unreliable
    )

    # Build the excluded-domains list (prediction markets always excluded).
    blocked = list(_POLYMARKET_EXCLUDED_DOMAINS)
    if exclude_domains:
        blocked.extend(d for d in exclude_domains if d not in blocked)

    # Tavily search tool — prediction-market aggregator sites excluded so
    # results reflect real-world evidence, not circular market prices.
    search_tool = TavilySearchResults(
        api_key=Config.TAVILY_API_KEY,
        max_results=5,
        search_depth="advanced",
        exclude_domains=blocked,
    )

    tools = [search_tool]
    agent_executor = create_react_agent(llm, tools)
    return agent_executor


def run_k2_agent(
    query: str,
    verbose: bool = False,
    max_retries: int = 3,
    system_prompt: Optional[str] = None,
    exclude_domains: Optional[List[str]] = None,
) -> dict:
    """Run the K2 agent on a query and return the final response.

    The agent will autonomously:
    1. Analyse the query
    2. Decide if it needs to search the web (Polymarket domains always excluded)
    3. Execute Tavily searches as needed
    4. Synthesise a final answer (with <think> blocks stripped)

    Args:
        query: The question or task to give the agent.
        verbose: If True, print intermediate reasoning steps.
        max_retries: Retries on transient 5xx server errors (default: 3).
        system_prompt: Optional system-level instructions prepended to the
            conversation. Use to control output format / persona.
        exclude_domains: Extra domains to block in Tavily on top of the default
            prediction-market exclusion list.

    Returns:
        dict with keys:
            - final_answer: Clean response text (no <think> blocks)
            - thinking: Raw chain-of-thought content (debug only)
            - messages: Full conversation history including tool calls
            - steps: Number of reasoning steps taken
    """
    agent = create_k2_agent(exclude_domains=exclude_domains)

    if verbose:
        print(f"🤖 K2 Agent Query: '{query}'\n")
        print("=" * 60)

    # Build input messages (optional system prompt first)
    input_messages: list = []
    if system_prompt:
        input_messages.append(SystemMessage(content=system_prompt))
    input_messages.append(HumanMessage(content=query))

    # Invoke with retry logic for transient 5xx errors
    for attempt in range(1, max_retries + 1):
        try:
            result = agent.invoke({"messages": input_messages})
            break
        except InternalServerError as exc:
            wait = 2 ** attempt
            if attempt < max_retries:
                msg = f"⚠️  K2 server busy (attempt {attempt}/{max_retries}). Retrying in {wait}s..."
                print(msg) if verbose else logger.warning(msg)
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"K2 API returned 'Server is busy' after {max_retries} attempts. "
                    "The K2 inference endpoint may be overloaded — try again in a minute."
                ) from exc
    
    messages = result["messages"]
    raw_final = messages[-1].content

    # Extract raw thinking for debug storage (never shown to users)
    thinking_match = re.search(r"<think>(.*?)</think>", raw_final, re.DOTALL | re.IGNORECASE)
    thinking_text = thinking_match.group(1).strip() if thinking_match else ""

    if verbose:
        for msg in messages:
            if isinstance(msg, HumanMessage):
                print(f"\n👤 Human: {msg.content}")
            elif isinstance(msg, AIMessage):
                if msg.tool_calls:
                    print(f"\n🧠 K2 is searching...")
                    for tc in msg.tool_calls:
                        print(f"   🔧 Tool: {tc['name']}")
                        print(f"   📝 Query: {tc['args'].get('query', '')}")
                else:
                    # Show clean version in verbose — strip thinking here too
                    print(f"\n🤖 K2 Response:\n{strip_thinking(msg.content)}")
            else:
                print(f"\n📊 Tool Result: {str(msg.content)[:200]}...")
        print("\n" + "=" * 60)

    return {
        "final_answer": strip_thinking(raw_final),   # clean — no <think> blocks
        "thinking": thinking_text,                    # raw CoT for debugging
        "messages": messages,
        "steps": len(messages),
    }


# System prompt used for market analysis runs.
# Instructs K2 to omit the <think> block from its final answer and to source
# only real-world information (not prediction-market prices).
_MARKET_ANALYSIS_SYSTEM_PROMPT = """\
You are MarketMind, an expert prediction market analyst with deep research skills.

IMPORTANT OUTPUT FORMAT:
- Do NOT include <think> or </think> tags in your final answer.
- Skip the chain-of-thought preamble — go straight to your structured analysis.
- Do NOT cite or rely on prediction-market sites (Polymarket, Manifold, Kalshi,
  Metaculus, PredictIt). Tavily has been configured to exclude them, but if any
  appear in results, ignore their prices. Only use real-world news, data, and
  expert analysis as evidence.

OUTPUT STRUCTURE:
1. **Summary** — one-paragraph overview of the market and key factors.
2. **Evidence** — bullet list of search findings with source URLs.
3. **Bull / Bear** — strongest arguments for YES and NO.
4. **Probability Estimate** — your best estimate (e.g. 62%).
5. **Thesis** — BUY | SELL | PASS with one-sentence rationale.
6. **Confidence** — how confident you are in this thesis (Low / Medium / High).
"""


def analyze_market_with_agent(market: dict) -> dict:
    """Use the K2 ReAct agent to deeply analyse a prediction market.

    Tavily is configured to exclude prediction-market aggregator sites so
    results reflect real-world evidence rather than circular market prices.
    K2's <think> block is stripped from the returned analysis.

    Args:
        market: dict with at least 'question' and 'description' keys.
            Optional keys: 'end_date', 'current_price' (for richer context).

    Returns:
        dict with:
            - analysis: Clean final-answer string (no <think> blocks)
            - thinking: Raw chain-of-thought (for debugging; not shown to users)
            - reasoning_steps: Number of agent steps taken
            - excluded_domains: Domains blocked from Tavily search
    """
    question = market.get("question", "N/A")
    description = market.get("description", "N/A")
    end_date = market.get("end_date", "unknown")
    current_price = market.get("current_price", "unknown")

    prompt = (
        f"**Market Question:** {question}\n"
        f"**Description:** {description}\n"
        f"**Resolution date:** {end_date}\n"
        f"**Current market price (YES):** {current_price}\n\n"
        "Search the web for recent news and data relevant to this market.\n"
        "Then provide your structured analysis following the format in the system prompt."
    )

    result = run_k2_agent(
        prompt,
        verbose=True,
        system_prompt=_MARKET_ANALYSIS_SYSTEM_PROMPT,
        # Prediction-market sites are already in the default exclusion list;
        # pass None here — create_k2_agent() always applies _POLYMARKET_EXCLUDED_DOMAINS.
        exclude_domains=None,
    )

    return {
        "analysis": result["final_answer"],
        "thinking": result["thinking"],   # chain-of-thought — strip before showing users
        "reasoning_steps": result["steps"],
        "excluded_domains": _POLYMARKET_EXCLUDED_DOMAINS,
    }


# Streaming support for real-time UX
def stream_k2_agent(query: str):
    """Stream the agent's reasoning process in real-time.
    
    This allows you to watch the agent think, search, and respond
    as it happens.
    
    Args:
        query: The question or task
        
    Yields:
        dict chunks with type and content
    """
    agent = create_k2_agent()
    
    # Stream events from the agent
    for event in agent.stream({"messages": [HumanMessage(content=query)]}):
        for key, value in event.items():
            if key == "agent":
                # Agent is thinking/responding
                messages = value.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage):
                        if last_msg.tool_calls:
                            yield {
                                "type": "tool_call",
                                "tool": last_msg.tool_calls[0]["name"],
                                "query": last_msg.tool_calls[0]["args"].get("query", ""),
                            }
                        else:
                            yield {
                                "type": "response",
                                "content": last_msg.content,
                            }
            elif key == "tools":
                # Tool results coming back
                yield {
                    "type": "tool_result",
                    "content": "Search completed",
                }


if __name__ == "__main__":
    # Demo: Run the agent on a test query
    import sys
    
    test_query = "What is the current status of GPT-5 development at OpenAI?"
    
    print("🚀 K2 ReAct Agent Demo\n")
    print(f"Testing with query: '{test_query}'\n")
    
    result = run_k2_agent(test_query, verbose=True)
    
    print("\n" + "=" * 60)
    print("📋 FINAL SUMMARY")
    print("=" * 60)
    print(f"Answer: {result['final_answer']}")
    print(f"Reasoning steps: {result['steps']}")
