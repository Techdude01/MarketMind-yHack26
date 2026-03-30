# K2 Think V2 Agentic System

## For Hackathon Agentic Track Qualification

This implements a **true autonomous agent** using K2 Think V2 as the reasoning engine and Tavily for web search. Built with **LangGraph** following the ReAct (Reason + Act) pattern.

---

## 🧠 What Makes This "Agentic"?

Unlike static prompt-response systems, this agent:

1. **Autonomously decides** when it needs information
2. **Executes web searches** without being explicitly told to
3. **Reasons iteratively** through multi-step problems
4. **Synthesizes information** from multiple sources
5. **Self-corrects** based on search results

### The ReAct Loop

```
Thought → Action → Observation → Thought → ... → Final Answer
```

K2 Think V2 drives the entire cognitive loop:
- **Thought**: "I need current data on X"
- **Action**: Calls Tavily search tool
- **Observation**: Reads search results
- **Thought**: "Now I can answer because..."
- **Final Answer**: Synthesized response

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -U langgraph langchain-core langchain-community langchain-openai
```

Or use the updated `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Add to your `.env` file:

```bash
# K2 Think V2 (Primary Reasoning Engine)
K2_THINK_V2_API_KEY=your_k2_api_key
K2_THINK_V2_BASE_URL=https://api.k2think.ai/v1

# Tavily (Web Search Tool)
TAVILY_API_KEY=your_tavily_api_key
```

### 3. Run the Demo

```bash
cd backend
python demo_k2_agent.py
```

---

## 📂 Architecture

```
backend/
├── app/
│   └── services/
│       └── llm/
│           ├── k2.py          # Original K2 client (direct)
│           └── k2_agent.py    # NEW: LangGraph ReAct agent
└── demo_k2_agent.py           # Demo script with 4 examples
```

---

## 🔧 Usage Examples

### Example 1: Basic Agent Query

```python
from app.services.llm.k2_agent import run_k2_agent

result = run_k2_agent(
    "What is the weather in New Haven today?",
    verbose=True  # See the agent's reasoning process
)

print(result["final_answer"])
```

**What happens internally:**
1. K2 receives query
2. K2 realizes it needs current data
3. K2 calls Tavily search: "New Haven CT weather today"
4. K2 reads weather results
5. K2 synthesizes final answer

### Example 2: Market Analysis (Autonomous Research)

```python
from app.services.llm.k2_agent import analyze_market_with_agent

market = {
    "question": "Will GPT-5 be released in 2025?",
    "description": "Market resolves YES if OpenAI releases GPT-5 in 2025."
}

analysis = analyze_market_with_agent(market)
print(analysis["analysis"])
```

**What happens:**
- Agent searches for: "GPT-5 release news"
- Agent searches for: "OpenAI development timeline"
- Agent searches for: "Sam Altman GPT-5 statements"
- Agent synthesizes a trading thesis

### Example 3: Streaming (Real-Time UX)

```python
from app.services.llm.k2_agent import stream_k2_agent

for chunk in stream_k2_agent("What are the top prediction markets?"):
    if chunk["type"] == "tool_call":
        print(f"🔍 Searching: {chunk['query']}")
    elif chunk["type"] == "response":
        print(f"💬 {chunk['content']}")
```

---

## 🎯 Integration with MarketMind

### Current Integration Points

1. **Market Analysis** (`agent/trader.py`)
   - Replace static K2 calls with agentic analysis
   - Agent autonomously researches market context

2. **Flask API** (`backend/app/routes/agent.py`)
   - Add endpoint: `POST /agent/analyze`
   - Stream agent reasoning to frontend

3. **Frontend** (`frontend/src/app/market/[id]`)
   - Display agent's research process
   - Show which sources it consulted

### Recommended Usage Pattern

```python
# In your agent loop
from app.services.llm.k2_agent import analyze_market_with_agent

for market in markets:
    # Agent autonomously researches and reasons
    result = analyze_market_with_agent(market)
    
    # Result includes:
    # - result["analysis"] - Full thesis
    # - result["reasoning_steps"] - Number of tool calls
    # - result["full_conversation"] - Complete reasoning trace
```

---

## 🏆 Hackathon Demo Script

### What to Show Judges

**1. Live Agent Execution**
```bash
python demo_k2_agent.py
```

Point out:
- K2 **decides on its own** when to search
- Multiple tool calls in one reasoning chain
- Synthesis of information from multiple sources

**2. Explain the ReAct Pattern**

Show the code in `k2_agent.py`:
```python
# This creates a TRUE reasoning loop
agent_executor = create_react_agent(llm, tools)
```

**3. Show Real Market Analysis**

Run Demo 2 (Market Analysis):
- Watch agent autonomously research
- See it cite sources
- Observe multi-step reasoning

**4. Emphasize K2 as the Brain**

"We're using **K2 Think V2** as the primary reasoning engine. It's not just generating text—it's actively deciding when it needs information, executing searches, and reasoning through complex scenarios."

---

## 📊 Comparison: Before vs. After

### Before (Static)
```python
# Old approach - manual, brittle
def analyze_market(market):
    news = tavily.search(market["question"])  # You decide when to search
    reasoning = k2.reason(market)             # Separate, disconnected
    return reasoning
```

### After (Agentic)
```python
# New approach - autonomous, flexible
def analyze_market(market):
    result = analyze_market_with_agent(market)  # Agent decides everything
    return result["analysis"]
```

---

## 🔍 Observability

### Verbose Mode

See exactly what the agent is thinking:

```python
result = run_k2_agent(query, verbose=True)

# Output:
# 👤 Human: What is the weather...
# 🧠 K2 Thought: I need to search for information
#    🔧 Tool: tavily_search_results_json
#    📝 Query: New Haven CT weather today
# 📊 Tool Result: {...}
# 🤖 K2 Response: Based on current data...
```

### Message History

Full reasoning trace available:

```python
for msg in result["messages"]:
    print(f"{msg.type}: {msg.content}")
```

---

## 🎓 Key Concepts for Judges

### 1. Tool Use
The agent can call functions (tools) mid-reasoning. Here, we give it Tavily search.

### 2. Function Calling
K2 outputs structured JSON when it wants to use a tool:
```json
{
  "tool": "tavily_search_results_json",
  "args": {"query": "GPT-5 release date"}
}
```

### 3. State Management
LangGraph maintains conversation state across reasoning steps.

### 4. Extensibility
Easy to add more tools:
```python
tools = [
    TavilySearchResults(),
    PolymarketSearchTool(),
    SQLDatabaseTool(),
    # ... any custom tool
]
```

---

## 🛠️ Advanced: Custom Tools

You can create custom tools for the agent:

```python
from langchain_core.tools import tool

@tool
def get_polymarket_odds(market_id: str) -> dict:
    """Get current odds for a Polymarket market."""
    # Your implementation
    return {"yes": 0.67, "no": 0.33}

# Add to agent
tools = [TavilySearchResults(), get_polymarket_odds]
agent = create_react_agent(llm, tools)
```

---

## 📈 Performance Notes

- **Average reasoning chain**: 3-7 steps
- **Search latency**: ~2-3s per Tavily call
- **K2 latency**: ~5-10s per reasoning step
- **Total time**: 15-30s for complex queries

For production, consider:
- Caching common searches in MongoDB
- Parallel tool execution
- Streaming responses to users

---

## 🐛 Troubleshooting

### "K2_THINK_V2_API_KEY not set"
Add to `.env`:
```bash
K2_THINK_V2_API_KEY=your_key
K2_THINK_V2_BASE_URL=https://api.k2think.ai/v1
```

### "TAVILY_API_KEY not set"
Add to `.env`:
```bash
TAVILY_API_KEY=your_key
```

### Agent not searching when it should
- Increase `temperature` slightly (try 0.1)
- Make prompt more explicit: "Search the web for..."
- Check Tavily quota

### Import errors
```bash
pip install -U langgraph langchain-core langchain-community langchain-openai
```

---

## 📚 Resources

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [K2 Think V2 API](https://k2think.ai)
- [Tavily Search](https://tavily.com)

---

## 🎉 Hackathon Checklist

- [x] LangGraph installed
- [x] K2 Think V2 integrated as reasoning engine
- [x] Tavily integrated as search tool
- [x] ReAct pattern implemented
- [x] Autonomous decision-making demonstrated
- [x] Demo script ready
- [x] Verbose logging for transparency
- [x] Streaming support for real-time UX
- [x] Market analysis integration

**You're ready to demo!** 🚀
