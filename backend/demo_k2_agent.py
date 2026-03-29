#!/usr/bin/env python3
"""Demo script for K2 Think V2 ReAct Agent.

This demonstrates the agentic capabilities for the hackathon.
Run with: python demo_k2_agent.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.services.llm.k2_agent import run_k2_agent, analyze_market_with_agent


def demo_basic_agent():
    """Demo 1: Basic agent query with web search."""
    print("\n" + "=" * 80)
    print("DEMO 1: Basic K2 Agent with Autonomous Web Search")
    print("=" * 80 + "\n")
    
    query = (
        "What is the weather in New Haven, CT today, "
        "and based on that, what should someone wear?"
    )
    
    result = run_k2_agent(query, verbose=True)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Query completed in {result['steps']} reasoning steps")
    print(f"📝 Final Answer: {result['final_answer'][:200]}...")


def demo_market_analysis():
    """Demo 2: Market analysis with autonomous research."""
    print("\n" + "=" * 80)
    print("DEMO 2: Autonomous Market Analysis")
    print("=" * 80 + "\n")
    
    # Mock market data
    market = {
        "question": "Will Donald Trump win the 2024 US Presidential Election?",
        "description": (
            "This market resolves to YES if Donald Trump wins the 2024 "
            "US Presidential Election. Otherwise resolves to NO."
        ),
    }
    
    result = analyze_market_with_agent(market)
    
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"✅ Analysis completed in {result['reasoning_steps']} steps")
    print(f"\n📊 FULL ANALYSIS:\n{result['analysis']}")


def demo_multi_step_research():
    """Demo 3: Complex multi-step research query."""
    print("\n" + "=" * 80)
    print("DEMO 3: Multi-Step Research Task")
    print("=" * 80 + "\n")
    
    query = (
        "Research the latest AI safety regulations being discussed in the US Congress. "
        "Then, assess how these might impact prediction markets about AI development. "
        "Finally, provide a trading thesis for markets about GPT-5 release timing."
    )
    
    result = run_k2_agent(query, verbose=True)
    
    print("\n" + "=" * 80)
    print("RESEARCH SUMMARY")
    print("=" * 80)
    print(f"✅ Research completed in {result['steps']} reasoning steps")
    print(f"📝 Thesis: {result['final_answer'][:300]}...")


def demo_streaming():
    """Demo 4: Streaming agent responses."""
    print("\n" + "=" * 80)
    print("DEMO 4: Streaming Agent (Real-Time Thinking)")
    print("=" * 80 + "\n")
    
    from app.services.llm.k2_agent import stream_k2_agent
    
    query = "What are the top 3 prediction markets on Polymarket right now?"
    
    print(f"🤖 Query: {query}\n")
    print("Streaming agent thoughts...\n")
    
    for chunk in stream_k2_agent(query):
        if chunk["type"] == "tool_call":
            print(f"🔍 Searching: {chunk['query']}")
        elif chunk["type"] == "tool_result":
            print(f"✅ Search completed")
        elif chunk["type"] == "response":
            print(f"\n💬 Final Answer:\n{chunk['content']}")


def main():
    """Run all demos."""
    print("\n" + "🚀" * 40)
    print("K2 THINK V2 AGENTIC SYSTEM DEMO")
    print("For hackathon agentic track qualification")
    print("🚀" * 40)
    
    # Check environment
    if not os.getenv("K2_THINK_V2_API_KEY"):
        print("❌ ERROR: K2_THINK_V2_API_KEY not set in .env")
        return
    
    if not os.getenv("TAVILY_API_KEY"):
        print("❌ ERROR: TAVILY_API_KEY not set in .env")
        return
    
    print("\n✅ Environment configured")
    
    # Uncomment the demos you want to run
    demos = [
        ("Basic Agent", demo_basic_agent),
        ("Market Analysis", demo_market_analysis),
        ("Multi-Step Research", demo_multi_step_research),
        ("Streaming", demo_streaming),
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    
    print("\nRunning Demo 1: Basic Agent...")
    demo_basic_agent()
    
    print("\n" + "=" * 80)
    print("Want to run more demos? Edit this script and uncomment them!")
    print("=" * 80)
    
    # Uncomment to run all:
    # for name, demo_fn in demos:
    #     try:
    #         demo_fn()
    #         input("\nPress Enter to continue to next demo...")
    #     except KeyboardInterrupt:
    #         print("\n\n👋 Demo interrupted. Exiting.")
    #         break
    #     except Exception as e:
    #         print(f"\n❌ Error in {name}: {e}")
    #         continue


if __name__ == "__main__":
    main()
