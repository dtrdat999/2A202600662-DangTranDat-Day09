"""End-to-end test client for the Legal Multi-Agent System.

Sends a legal question to the Law Agent directly (bypassing Customer Agent) to reduce latency.
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

LAW_AGENT_URL = os.getenv("LAW_AGENT_URL", "http://localhost:10101")
A2A_API_KEY = os.getenv("A2A_API_KEY", "super-secret-key")

import sys
sys.stdout.reconfigure(encoding='utf-8')

QUESTION = (
    "Nếu công ty vi phạm hợp đồng, trốn thuế và đánh cắp dữ liệu người dùng "
    "thì hậu quả pháp lý là gì?"
)


async def main() -> None:
    import time
    start_time = time.time()

    print(f"Connecting to Law Agent (bypassing Customer Agent for lower latency) at {LAW_AGENT_URL}")
    print(f"Question: {QUESTION}")
    print("-" * 60)
    
    headers = {"Authorization": f"Bearer {A2A_API_KEY}"}

    async with httpx.AsyncClient(timeout=300.0, headers=headers) as http_client:
        # Resolve agent card
        card_url = f"{LAW_AGENT_URL}/.well-known/agent.json"
        try:
            card_resp = await http_client.get(card_url)
            card_resp.raise_for_status()
        except Exception as e:
            print(f"ERROR: Could not reach Law Agent at {card_url}")
            print(f"  {e}")
            print("Make sure all services are running (./start_all.ps1)")
            sys.exit(1)

        from a2a.types import AgentCard, Message, Part, Role, TextPart, MessageSendParams
        from a2a.client import A2AClient
        from uuid import uuid4

        agent_card = AgentCard.model_validate(card_resp.json())
        print(f"Connected to agent: {agent_card.name} v{agent_card.version}")
        print("-" * 60)

        # Build the legacy A2AClient
        client = A2AClient(httpx_client=http_client, agent_card=agent_card)

        # Construct the message
        from a2a.types import SendMessageRequest, MessageSendParams as MSP
        message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=QUESTION))],
            message_id=str(uuid4()),
        )
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MSP(message=message),
        )

        print("Sending request (this may take 15-30s while agents chain)...\n")
        response = await client.send_message(request)

        # Parse response
        result_text = ""
        if hasattr(response, "root"):
            root = response.root
            if hasattr(root, "result"):
                result = root.result
                # Task with artifacts
                if hasattr(result, "artifacts") and result.artifacts:
                    for artifact in result.artifacts:
                        for part in artifact.parts:
                            p = part.root if hasattr(part, "root") else part
                            if hasattr(p, "text"):
                                result_text += p.text
                # Message with parts
                elif hasattr(result, "parts") and result.parts:
                    for part in result.parts:
                        p = part.root if hasattr(part, "root") else part
                        if hasattr(p, "text"):
                            result_text += p.text

        end_time = time.time()
        latency = end_time - start_time

        if result_text:
            print("RESPONSE:")
            print("=" * 60)
            print(result_text)
            print("=" * 60)
            print(f"✅ Total Latency: {latency:.2f} seconds")
            print("💡 Extra Credit: Bypassing Customer Agent and connecting directly to Law Agent reduces latency significantly!")
        else:
            print("No text response received. Raw response:")
            print(response)


if __name__ == "__main__":
    asyncio.run(main())
