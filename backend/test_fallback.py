import asyncio
from app.services.llm.k2_agent import run_k2_agent

res = run_k2_agent("Tim Walz 2028 Democratic presidential nomination prospects", verbose=True)
print(res["final_answer"])
