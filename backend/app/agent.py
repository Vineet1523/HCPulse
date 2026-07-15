from datetime import datetime
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from .database import settings
from .schemas import AgentDecision
from .tools import TOOLS

class AgentState(TypedDict, total=False):
    message: str
    current_form: dict
    decision: dict
    tool_result: str
    response: str

def llm():
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to the project .env file.")
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0,
    )

def understand(state: AgentState):
    model = llm().with_structured_output(AgentDecision)
    cf = state.get("current_form") or {}
    
    prompt = f"""
You are the reasoning layer of an AI-first life-sciences CRM for field representatives.
Current local date/time: {datetime.now().isoformat(timespec='minutes')}

Active Draft State (already entered by representative):
{cf}

Choose exactly one CRM tool:
- log_interaction: Use this for ALL actions related to the draft form (creating a draft, describing a meeting, updating fields, correcting draft values like names, topics, or sentiments). Set is_commit = false for updates/corrections, and is_commit = true only when saving/done.
- edit_interaction: Use this ONLY to modify a record that is already successfully logged in the database.
- get_hcp_history: retrieve previous meetings.
- schedule_follow_up: create a follow-up activity.
- generate_hcp_insights: analyze engagement and recommend a next action.

CRITICAL: Any message that corrects draft values (such as HCP name typos like 'sorry the name was Dr. Suhas Verma'), describes draft meeting details, or updates any values in the 'Active Draft State' MUST select tool = 'log_interaction' and set is_commit = false. Do not choose edit_interaction for draft form corrections.

For log_interaction:
* is_commit: Set to true if the user's message is confirming, logging, saving, or saying "done", "okay", "log it", "save", "yes", "proceed". Set to false if they are providing new details, updates, or correcting fields.
* hcp_name: Extract or update the HCP name. If the user corrects the name (e.g. "sorry the name was Dr. Ananya Khan" or "sorry the name wad Dr.Suhas verma"), output the corrected name. Otherwise, default to "{cf.get('hcp_name', '')}".
* topics: Extract key discussion points, or merge/update if they provide new topics. Default to "{cf.get('topics', '')}".
* outcomes: Extract or update key outcomes/milestones. Default to "{cf.get('outcomes', '')}".
* samples_distributed: Extract or update samples. Default to "{cf.get('samples_distributed', '')}".
* materials_shared: Extract or update materials. Default to "{cf.get('materials_shared', '')}".
* sentiment: Positive, Neutral, or Negative based on text. Default to "{cf.get('sentiment', 'Neutral')}".
* follow_up_required: boolean. Default to {str(cf.get('follow_up_required', False)).lower()}.

Do not invent a different HCP. Output only structured data.
"""
    decision = model.invoke([SystemMessage(content=prompt), HumanMessage(content=state["message"])])
    return {"decision": decision.model_dump()}

def route(state: AgentState):
    return state["decision"]["tool"]

def run_tool(state: AgentState):
    d = state["decision"]
    name = d["tool"]
    cf = state.get("current_form") or {}
    
    if name == "log_interaction":
        if not d.get("is_commit"):
            return {"tool_result": "Draft updated."}
            
        args = {
            "hcp_name": cf.get("hcp_name") or d.get("hcp_name") or "Unknown HCP",
            "topics": cf.get("topics") or d.get("topics") or "Interaction logged via AI assistant.",
            "interaction_type": cf.get("interaction_type") or d.get("interaction_type") or "Meeting",
            "interaction_date": cf.get("interaction_date") or d.get("interaction_date") or "",
            "attendees": cf.get("attendees") or d.get("attendees") or "",
            "materials_shared": cf.get("materials_shared") or d.get("materials_shared") or "",
            "sentiment": cf.get("sentiment") or d.get("sentiment") or "Neutral",
            "follow_up_required": bool(cf.get("follow_up_required") if "follow_up_required" in cf else d.get("follow_up_required")),
            "outcomes": cf.get("outcomes") or d.get("outcomes") or "",
            "samples_distributed": cf.get("samples_distributed") or d.get("samples_distributed") or "",
        }
    elif name == "edit_interaction":
        args = {"hcp_name": d["hcp_name"], "field": d.get("field") or "", "new_value": d.get("new_value") or ""}
    elif name in {"get_hcp_history", "generate_hcp_insights"}:
        args = {"hcp_name": d["hcp_name"]}
    else:
        args = {
            "hcp_name": d["hcp_name"],
            "follow_up_date": d.get("follow_up_date") or "",
            "purpose": d.get("purpose") or "HCP follow-up",
        }
    result = TOOLS[name].invoke(args)
    return {"tool_result": result}

def respond(state: AgentState):
    d = state["decision"]
    tool_name = d["tool"]
    tool_res = state["tool_result"]
    
    if tool_res.startswith("Error") or "missing" in tool_res.lower() or "not found" in tool_res.lower():
        return {"response": tool_res}
        
    model = llm()
    
    if tool_name == "log_interaction":
        if not d.get("is_commit"):
            prompt = f"""You are a professional life-sciences CRM assistant.
The representative said: "{state['message']}"
We updated the draft interaction on the left.

Write a friendly response confirming that the draft was updated on the left (mention any key fields changed like HCP Name or topics if corrected).
Tell them to say 'done' or click the manual 'Log Interaction' button when they are ready to save.
Keep it extremely concise (1-2 sentences max).
"""
            out = model.invoke([SystemMessage(content=prompt)])
            return {"response": out.content}
        else:
            prompt = f"""You are a professional life-sciences CRM assistant.
The representative confirmed to save: "{state['message']}"
The log_interaction tool returned: "{tool_res}"

Write a friendly response confirming that the interaction was logged successfully.
Explicitly state that the details (HCP Name, Date, Sentiment, and Materials) have been automatically populated based on their summary.
Ask if they would like you to suggest a specific follow-up action, such as scheduling a meeting.
Match this style and wording exactly:
"✅ **Interaction logged successfully!** The details (HCP Name, Date, Sentiment, and Materials) have been automatically populated based on your summary. Would you like me to suggest a specific follow-up action, such as scheduling a meeting?"
Do not add any other text. Output only this block.
"""
            out = model.invoke([SystemMessage(content=prompt)])
            return {"response": out.content}
            
    elif tool_name == "generate_hcp_insights" and not tool_res.startswith("No "):
        prompt = """You are a life-sciences field sales CRM assistant.
Based only on the CRM history below, produce a short HCP insight with exactly these labels:
Engagement Level:
Key Interest:
Recommended Next Action:
Suggested Talking Point:
Do not make clinical claims or prescribe treatment.
"""
        out = model.invoke([SystemMessage(content=prompt), HumanMessage(content=tool_res)])
        return {"response": out.content}
        
    return {"response": tool_res}

builder = StateGraph(AgentState)
builder.add_node("understand", understand)
for name in TOOLS:
    builder.add_node(name, run_tool)
builder.add_node("respond", respond)
builder.add_edge(START, "understand")
builder.add_conditional_edges("understand", route, {name: name for name in TOOLS})
for name in TOOLS:
    builder.add_edge(name, "respond")
builder.add_edge("respond", END)
hcp_graph = builder.compile()

def run_agent(message: str, current_form: dict | None = None):
    result = hcp_graph.invoke({"message": message, "current_form": current_form})
    return {
        "response": result["response"],
        "tool_used": result["decision"]["tool"],
        "extracted": result["decision"],
    }
