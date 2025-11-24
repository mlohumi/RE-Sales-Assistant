from ninja import Router
from api_layer.schemas import ConversationCreateResponse
from properties.models import ConversationSession
from agent.state import AgentState

router = Router(tags=["Conversations"])


@router.post("", response=ConversationCreateResponse)
def create_conversation(request):
    session = ConversationSession.objects.create(state={})

    # initialize state
    state = AgentState(
        conversation_id=session.id,
        messages=[]
    )

    greeting = (
        "Hello! 👋 I'm your SilverLand Property Assistant. "
        "Which city are you looking to buy in?"
    )

    state.messages.append({"role": "assistant", "content": greeting})

    # save state into DB
    session.state = state.model_dump(mode="json")

    session.save()

    return ConversationCreateResponse(
        conversation_id=session.id,
        message=greeting
    )
