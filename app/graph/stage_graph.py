"""Per-stage LangGraph agent graph.

Constructs a compiled state machine that:
1. Assembles context (system + prior stage + dictionary + current draft + user message)
2. Calls the LLM (which may request tools)
3. Executes tool calls if needed (loops back to step 2)
4. Finalizes structured output

All stages reuse the same graph; inputs differ (prompt, prior context, etc.).
"""

from typing import Literal

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import StateGraph, START, END

from app.agents.llm import get_chat_model
from app.agents.outputs import StageResult
from app.core.logging import get_logger
from app.graph.state import StageState
from app.graph.tools import lookup_dictionary

log = get_logger(__name__)


def build_input(state: StageState) -> dict:
    """Build the initial message list from context.

    Prepends a SystemMessage with the system prompt if no messages exist yet.
    Then appends a HumanMessage assembling all context (prior docs, dictionary, current draft).
    """
    messages: list[BaseMessage] = list(state.get("messages", []))

    system_msg = SystemMessage(content=state["system_prompt"])
    messages.insert(0, system_msg)

    context_block = ""
    if state["prior_context"]:
        context_block += f"**Prior Context from Previous Stages:**\n{state['prior_context']}\n\n"
    if state["dictionary_text"]:
        context_block += f"**Available Tables/Data Dictionary:**\n{state['dictionary_text']}\n\n"
    if state["current_draft"]:
        context_block += f"**Current Draft:**\n{state['current_draft']}\n\n"

    human_msg = HumanMessage(content=context_block if context_block else "Please proceed.")
    messages.append(human_msg)

    return {"messages": messages}


def call_model(state: StageState) -> dict:
    """Call the LLM with tools bound.

    The model can request the `lookup_dictionary` tool. If it does, we'll route to
    `run_tool` via the conditional edge. Otherwise, we route to `finalize`.
    """
    model = get_chat_model(state["stage"])
    model_with_tools = model.bind_tools([lookup_dictionary])

    messages = state["messages"]
    response = model_with_tools.invoke(messages)

    return {"messages": [response]}


def run_tool(state: StageState) -> dict:
    """Execute the tool call(s) from the last AIMessage.

    Appends ToolMessage results back to the message list for the next LLM call.
    """
    messages = list(state["messages"])
    last_message = messages[-1]

    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {}

    tool_results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]

        if tool_name == "lookup_dictionary":
            result = lookup_dictionary.invoke(tool_input)
        else:
            result = f"Unknown tool: {tool_name}"

        tool_results.append(
            ToolMessage(
                content=result,
                tool_call_id=tool_call["id"],
            )
        )

    return {"messages": tool_results}


def finalize(state: StageState) -> dict:
    """Finalize the response as structured output.

    Calls the model with `with_structured_output(StageResult)` to force the
    response into the expected shape.
    """
    model = get_chat_model(state["stage"])
    model_structured = model.with_structured_output(StageResult)

    messages = state["messages"]
    result = model_structured.invoke(messages)

    return {"result": result}


def route_after_call_model(state: StageState) -> Literal["run_tool", "finalize"]:
    """Route based on whether the model requested a tool."""
    messages = state["messages"]
    if not messages:
        return "finalize"

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "run_tool"
    return "finalize"


def build_stage_graph() -> object:
    """Build and compile the per-stage agent graph.

    Returns a compiled StateGraph ready to invoke with a StageState.
    """
    graph = StateGraph(StageState)

    graph.add_node("build_input", build_input)
    graph.add_node("call_model", call_model)
    graph.add_node("run_tool", run_tool)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "build_input")
    graph.add_edge("build_input", "call_model")
    graph.add_conditional_edges(
        "call_model",
        route_after_call_model,
        {
            "run_tool": "run_tool",
            "finalize": "finalize",
        },
    )
    graph.add_edge("run_tool", "call_model")
    graph.add_edge("finalize", END)

    return graph.compile()


stage_graph = build_stage_graph()
