import asyncio
import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

# Ensure we can import from stages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stages.stage_4_milti_agent.main import create_graph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

app = FastAPI(title="Stage 4 Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo MemorySaver và Graph 1 lần duy nhất cho toàn bộ app
memory = MemorySaver()
graph = create_graph(checkpointer=memory)

class ChatRequest(BaseModel):
    question: str
    thread_id: str = "default_session"

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    
    initial_state = {
        "question": req.question,
        "chat_history": [HumanMessage(content=req.question)],
        "law_analysis": "",
        "needs_tax": False,
        "needs_compliance": False,
        "needs_privacy": False,
        "tax_result": "",
        "compliance_result": "",
        "privacy_analysis": "",
        "final_answer": "",
    }
    
    config = {"configurable": {"thread_id": req.thread_id}}
    
    result = await graph.ainvoke(initial_state, config=config)
    
    return {
        "final_answer": result.get("final_answer", ""),
        "tax_result": result.get("tax_result", ""),
        "compliance_result": result.get("compliance_result", ""),
        "privacy_result": result.get("privacy_analysis", ""),
        "law_analysis": result.get("law_analysis", "")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
