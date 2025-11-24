from ninja import Router
from django.shortcuts import get_object_or_404

from api_layer.schemas import ChatRequest, ChatResponse, ProjectItem
from properties.models import ConversationSession
from agent.state import AgentState
from agent.langgraph_graph import build_graph

router = Router(tags=["Chat"])

graph = build_graph()
app = graph.compile()


@router.post("/chat", response=ChatResponse)
def chat_with_agent(request, payload: ChatRequest):
    session = get_object_or_404(
        ConversationSession, pk=payload.conversation_id
    )

    prev_state = AgentState(**session.state)

    # Add user message
    prev_state.messages.append({
        "role": "user",
        "content": payload.message
    })

    # Run LangGraph
    new_state_dict = app.invoke(prev_state.dict())
    new_state = AgentState(**new_state_dict)

    # Save updated state
    session.state = new_state.model_dump(mode="json")

    session.save()

    # Get last assistant message
    last_assistant_msg = next(
        (m["content"] for m in reversed(new_state.messages) if m["role"] == "assistant"),
        ""
    )

    shortlisted = [
        ProjectItem(
            id=p.id,
            name=p.name,
            city=p.city,
            country=p.country,
            price_usd=p.price_usd,
            unit_type=p.unit_type,
            no_of_bedrooms=p.no_of_bedrooms,
            property_type=p.property_type
        )
        for p in new_state.candidate_projects
    ]

    return ChatResponse(
        conversation_id=session.id,
        reply=last_assistant_msg,
        shortlisted_projects=shortlisted,
        agent_state=new_state.dict()
    )
