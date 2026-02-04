from os import getenv , path
from agno.agent import Agent, RunEvent
from agno.models.openai import OpenAIResponses
from .db import db
from .agent_prompt import SystemPrompt
from .document import knowledge
from typing import Iterator
from dotenv import load_dotenv
load_dotenv()
project_root = path.dirname(path.abspath(__file__))

def get_agent():
    agent = Agent(
        model=OpenAIResponses(id=getenv('OPENAI_MODEL_NAME')),
        db=db,
        description=(
            "A document Q&A assistant that answers questions strictly based "
            "on uploaded PDF documents using Retrieval-Augmented Generation (RAG)."
        ),
        instructions=SystemPrompt,
        knowledge=knowledge,
        search_knowledge=True,
        read_chat_history=True,
        debug_mode=False,
        add_history_to_context=True,
    )
    return agent

def get_response_stream(query: str, session_id: str) -> Iterator[str]:
    agent = get_agent()
    for event in agent.run(query, session_id=session_id, stream=True, stream_events=True):
        if event.event == RunEvent.tool_call_started:
            if event.tool.tool_name == "search_knowledge_base":
                yield '< Exploring >'
        if event.event == RunEvent.reasoning_step:
            yield f"< Thinking >"
        if event.event == RunEvent.run_content:
            if event.content:
                yield event.content