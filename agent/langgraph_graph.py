import json
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from agent.state import AgentState, BuyerProfile
from agent.llm_client import LLMClient
from agent.tools.t2sql_tool import project_sql_tool
from agent.tools.booking_tool import create_lead_and_booking
from agent.tools.project_info_tool import get_project_details

from agent.tools.web_search_tool import web_search_tool





llm = LLMClient()


def user_input_node(state: AgentState) -> AgentState:
    """
    Entry node: state already includes the latest user message,
    added by the API layer.
    """
    return state


def intent_classification_node(state: AgentState) -> AgentState:
    """
    Uses GPT-4o (via LLMClient) to:
      - classify the user's intent
      - extract buyer preferences:
          city, budget_min, budget_max, unit_size, bedrooms, property_type

    Allowed intent values from the LLM:
      - "prefs"
      - "book"
      - "detail"
      - "generic"

    We then map those to internal states:
      - "prefs"  -> state.intent = "collect_prefs"
      - "book"   -> state.intent = "book_visit"
      - "detail" -> state.intent = "project_detail"
      - "generic"-> state.intent = "generic"
    """

    last_user_msg = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    if not last_user_msg:
        state.intent = "generic"
        return state

    system_prompt = """
You are a real-estate assistant that extracts buyer intent and preferences from user messages.

Your job is to:
  1. Decide the user's intent.
  2. Extract structured preference fields when relevant.

You MUST respond ONLY with a valid JSON object with these exact keys:
- intent: one of ["prefs", "book", "detail", "generic"]
- city: string or null
- budget_min: integer or null
- budget_max: integer or null
- unit_size: string or null
- bedrooms: integer or null
- property_type: string or null
- lead_first_name: string or null
- lead_last_name: string or null
- lead_email: string or null

Rules for 'intent':
- If the user expresses ANY property requirements (e.g. city, area, number of bedrooms, BHK, price/budget, type like apartment/villa),
  set "intent" = "prefs", even if some fields (like budget) are missing.
- If the user clearly wants to schedule, book, confirm, or request a visit/viewing/tour of a property,
  set "intent" = "book".
- If the user asks for more information about a specific project (by number from a list or by name),
  and is not yet explicitly booking, set "intent" = "detail".
- If the user is chatting, asking general questions, or talking about something
  unrelated to real-estate buying and visits, set "intent" = "generic".

Rules for fields:
- city: best guess of the city or area if mentioned; otherwise null.
- budget_min / budget_max:
    - If a single budget is given (e.g. "up to 300000 USD"), use null for budget_min
      and that number for budget_max.
    - If a range is given (e.g. "from 200k to 350k"), convert to integers and fill both.
    - If values like "50 lakhs" or "0.5 million" are used, convert to an approximate integer.
- unit_size: use labels like "1BHK", "2BHK", "3BHK", "studio" where possible.
- bedrooms: numeric version of size where clear (e.g. 2 for 2BHK, 1 for 1BHK/studio).
- property_type: normalize to a simple type like "apartment", "villa", "townhouse", "studio" where clear; otherwise null.
- If the user mentions their name (e.g. "I'm Mukesh", "My name is John"), fill lead_first_name and lead_last_name if possible.
- If the user mentions an email address, fill lead_email.

Output format:
- Do NOT include any explanations, comments, or extra text.
- Do NOT wrap JSON in markdown.
- ONLY output the raw JSON object.
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": last_user_msg},
    ]

    data: Dict[str, Any] = {}

    try:
        raw = llm.chat(messages)

        # Try to isolate the JSON object in case the model adds extra text
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            raw_json = raw[start : end + 1]
        else:
            raw_json = raw

        data = json.loads(raw_json)
    except Exception:
        # If parsing fails, fall back to generic
        state.intent = "generic"
        return state

    # ---------- intent mapping ----------
    intent_raw = (data.get("intent") or "").lower().strip()
    if intent_raw == "prefs":
        state.intent = "collect_prefs"
    elif intent_raw == "book":
        state.intent = "book_visit"
    elif intent_raw == "detail":
        state.intent = "project_detail"
    else:
        state.intent = "generic"

    # ---------- fill BuyerProfile ----------
    profile: BuyerProfile = state.buyer_profile

    city = data.get("city")
    if city:
        profile.city = city

    budget_min = data.get("budget_min")
    if isinstance(budget_min, (int, float)):
        profile.budget_min = int(budget_min)

    budget_max = data.get("budget_max")
    if isinstance(budget_max, (int, float)):
        profile.budget_max = int(budget_max)

    unit_size = data.get("unit_size")
    if unit_size:
        profile.unit_size = unit_size

    bedrooms = data.get("bedrooms")
    if isinstance(bedrooms, int):
        profile.bedrooms = bedrooms

    property_type = data.get("property_type")
    if property_type:
        profile.property_type = property_type

    state.buyer_profile = profile

    # ---------- fill LeadInfo (optional early capture) ----------
    lead = state.lead_info

    lead_first_name = data.get("lead_first_name")
    if isinstance(lead_first_name, str) and lead_first_name.strip():
        lead.first_name = lead_first_name.strip()

    lead_last_name = data.get("lead_last_name")
    if isinstance(lead_last_name, str) and lead_last_name.strip():
        lead.last_name = lead_last_name.strip()

    lead_email = data.get("lead_email")
    if isinstance(lead_email, str) and "@" in lead_email:
        lead.email = lead_email.strip()

    state.lead_info = lead

    return state



def router_node(state: AgentState) -> str:
    """
    Decide which node to go to after intent classification.
    """

    # Preference collection flow
    if state.intent == "collect_prefs":
        p = state.buyer_profile
        # If we know enough, go straight to DB search
        if p.city and (p.unit_size or p.bedrooms is not None) and p.budget_max is not None:
            return "t2sql_node"
        # Otherwise, clarify missing info
        return "clarify_prefs_node"

    # Booking flow
    if state.intent == "book_visit":
        return "booking_node"

    # Project detail flow
    if state.intent == "project_detail":
        return "project_detail_node"

    # Fallback: generic chat
    return "respond_node"


def clarify_prefs_node(state: AgentState) -> AgentState:
    """
    Ask the buyer for missing key preferences:
      - city
      - unit size / bedrooms
      - budget_max
    """

    p = state.buyer_profile
    questions = []

    if not p.city:
        questions.append("Which city are you looking to buy in?")
    if not (p.unit_size or p.bedrooms):
        questions.append("What unit size are you interested in (e.g., 1BHK, 2BHK, 3BHK)?")
    if p.budget_max is None:
        questions.append("What is your approximate maximum budget (in USD)?")

    if not questions:
        text = "Could you please confirm your city, preferred unit size, and budget range?"
    else:
        text = " ".join(questions)

    state.messages.append({"role": "assistant", "content": text})
    state.stage = "asking_prefs"
    return state


def t2sql_node(state: AgentState) -> AgentState:
    """
    Call our 'SQL tool' (ProjectSqlTool) to search for matching projects
    based on buyer_profile.
    """

    projects = project_sql_tool.search_projects_by_profile(state.buyer_profile)
    state.candidate_projects = projects
    state.stage = "recommendations"

    if not projects:
        msg = (
            "I couldn't find an exact match for your preferences. "
            "I can suggest nearby locations or slightly different budgets if you'd like."
        )
        state.messages.append({"role": "assistant", "content": msg})
    else:
        lines = ["Here are some projects matching your preferences:"]
        for idx, p in enumerate(projects, start=1):
            if p.price_usd:
                price_text = f"{p.price_usd:,.0f} USD"
            else:
                price_text = "Price on request"
            lines.append(
                f"{idx}. {p.name} in {p.city}, {p.country} – approx. price: {price_text} "
                f"({p.unit_type or 'unit'})"
            )
        lines.append("Would you like to know more about any of these, or book a property visit?")
        state.messages.append({"role": "assistant", "content": "\n".join(lines)})

    return state



def project_detail_node(state: AgentState) -> AgentState:
    """
    Returns detailed information about a selected project.

    - Tries to infer which project the user means (e.g. "first project", "project 2",
      or by project name) using LLM.
    - If still unclear, asks user to choose from the shortlist.
    """

    # Get the last user message
    last_user_msg = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # -------------------------------------------
    # 1) Try to infer project choice via LLM if not already selected
    # -------------------------------------------
    if not state.selected_project_id and state.candidate_projects:
        project_list_text = ""
        lines = []
        for idx, p in enumerate(state.candidate_projects, start=1):
            lines.append(f"{idx}. {p.name} in {p.city}, {p.country}")
        project_list_text = "\n".join(lines)

        system_prompt = """
You are a project selection extraction assistant for a real estate chatbot.

Given:
  - a list of shortlisted projects (with indices and names)
  - the user's latest message

You MUST extract which project the user is referring to.

Respond ONLY with a JSON object with these keys:
- project_index: integer or null          # 1-based index from the shortlist, if user picked by number or position
- project_name: string or null            # project name or close match, if user mentions name

Rules:
- If the user says things like "first one", "first project", "project 1", "1st project",
  convert that into project_index = 1.
- If the user says "second project", "project 2", "2nd project", set project_index = 2, etc.
- If the user says "any project", "any of them is fine", assume project_index = 1.
- If both index and name are unclear, set both project_index and project_name to null.
- Do NOT include explanations. Output ONLY the JSON object.
""".strip()

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "system",
                "content": f"Shortlisted projects:\n{project_list_text}" if project_list_text else "No shortlisted projects yet."
            },
            {"role": "user", "content": last_user_msg},
        ]

        extracted = {}
        try:
            raw = llm.chat(messages)
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                raw_json = raw[start : end + 1]
            else:
                raw_json = raw
            extracted = json.loads(raw_json)
        except Exception:
            extracted = {}

        if extracted:
            project_index = extracted.get("project_index")
            project_name = extracted.get("project_name")

            # Try by index first
            if isinstance(project_index, int):
                idx0 = project_index - 1
                if 0 <= idx0 < len(state.candidate_projects):
                    state.selected_project_id = state.candidate_projects[idx0].id

            # If still None, try fuzzy match by name
            if not state.selected_project_id and project_name:
                pname_lower = project_name.lower()
                for p in state.candidate_projects:
                    if p.name.lower() in pname_lower or pname_lower in p.name.lower():
                        state.selected_project_id = p.id
                        break

    # -------------------------------------------
    # 2) If still no selection, ask user to choose
    # -------------------------------------------
    if not state.selected_project_id:
        if state.candidate_projects:
            lines = ["Which project do you want details for?"]
            for idx, p in enumerate(state.candidate_projects, start=1):
                lines.append(f"{idx}. {p.name} in {p.city}")
            state.messages.append({"role": "assistant", "content": "\n".join(lines)})
        else:
            state.messages.append({
                "role": "assistant",
                "content": "Which project would you like details about?"
            })
        state.stage = "detail_need_selection"
        return state

    # -------------------------------------------
    # 3) We have a selected_project_id → fetch details
    # -------------------------------------------
        details = get_project_details(state.selected_project_id)

    if not details:
        # Try web search as a fallback for extra information
        # We only know the selected_project_id, so we need to look it up briefly
        from properties.models import Project

        project_name = None
        city = None
        try:
            p = Project.objects.get(id=state.selected_project_id)
            project_name = p.name
            city = p.city
        except Project.DoesNotExist:
            pass

        if project_name:
            summary = web_search_tool.search_project_info(project_name=project_name, city=city)
        else:
            summary = None

        if summary:
            state.messages.append({
                "role": "assistant",
                "content": (
                    f"I couldn't find structured details for this project in my database, "
                    f"but here's what I found from external sources about **{project_name}**:\n\n"
                    f"{summary}"
                ),
            })
            state.stage = "detail_from_web"
        else:
            state.messages.append({
                "role": "assistant",
                "content": (
                    "I'm unable to find that project's details in my data or through external search. "
                    "Could you try a different project or ask for general buying guidance?"
                ),
            })
            state.stage = "detail_error"

        return state


    lines = [
        f"**{details['name']}** – Full Details:",
        "",
        f"🏙 **Location:** {details['city']}, {details['country']}",
        f"🏗 **Developer:** {details['developer_name']}" if details["developer_name"] else "",
        f"🛏 **Bedrooms:** {details['no_of_bedrooms']}" if details["no_of_bedrooms"] is not None else "",
        f"🛁 **Bathrooms:** {details['bathrooms']}" if details["bathrooms"] is not None else "",
        f"🏠 **Property Type:** {details['property_type']}" if details["property_type"] else "",
        f"📐 **Area:** {details['area_sqm']} sq. m." if details["area_sqm"] else "",
        f"💰 **Price:** {details['price_usd']} USD" if details["price_usd"] else "",
        f"📅 **Completion Status:** {details['completion_status']}" if details["completion_status"] else "",
        f"🗓 **Completion Date:** {details['completion_date']}" if details["completion_date"] else "",
        "",
        f"✨ **Features:**\n{details['features']}" if details["features"] else "",
        "",
        f"🏢 **Facilities:**\n{details['facilities']}" if details["facilities"] else "",
        "",
        f"📝 **Description:**\n{details['description']}" if details["description"] else "",
    ]

    result = "\n".join([line for line in lines if line.strip()])

    state.messages.append({"role": "assistant", "content": result})
    state.stage = "detail_complete"
    return state



def booking_node(state: AgentState) -> AgentState:
    """
    Handles the booking flow:
      - tries to infer which project the user wants to visit
      - tries to extract lead contact (name + email)
      - if both project + contact are available, creates Lead + Booking in DB
      - otherwise, asks targeted questions and waits for next turn
    """

    # Get the last user message
    last_user_msg = ""
    for msg in reversed(state.messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # -------------------------------------------
    # 1) Try to extract project choice + contact via LLM
    # -------------------------------------------

    project_list_text = ""
    if state.candidate_projects:
        # Provide indexed list so LLM can map "project 1" etc.
        lines = []
        for idx, p in enumerate(state.candidate_projects, start=1):
            lines.append(f"{idx}. {p.name} in {p.city}, {p.country}")
        project_list_text = "\n".join(lines)

    system_prompt = """
You are a booking extraction assistant for a real estate chatbot.

Given:
  - a list of shortlisted projects (with indices and names)
  - the user's latest message

You MUST extract:
  - which project (by index or name) the user wants to visit, if any
  - the user's email, if mentioned
  - the user's first name, if clearly mentioned

Respond ONLY with a JSON object with these keys:
- project_index: integer or null          # 1-based index from the shortlist, if user picked by number
- project_name: string or null            # project name or close match, if user mentions name
- email: string or null
- first_name: string or null

Rules:
- If the user says things like "first one", "project 1", "the second project",
  convert that into the appropriate project_index.
- If both index and name are unclear, set both project_index and project_name to null.
- If email is not present, use null.
- If first name is not clear, use null.

Do NOT include explanations. Output ONLY the JSON object.
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": f"Shortlisted projects:\n{project_list_text}" if project_list_text else "No shortlisted projects yet."
        },
        {"role": "user", "content": last_user_msg},
    ]

    try:
        raw = llm.chat(messages)
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            raw_json = raw[start : end + 1]
        else:
            raw_json = raw
        extracted = json.loads(raw_json)
    except Exception:
        extracted = {}

    # -------------------------------------------
    # 2) Update selected_project_id from extracted info
    # -------------------------------------------
    if state.candidate_projects and extracted and not state.selected_project_id:
        project_index = extracted.get("project_index")
        project_name = extracted.get("project_name")

        # Try by index first
        if isinstance(project_index, int):
            idx0 = project_index - 1
            if 0 <= idx0 < len(state.candidate_projects):
                state.selected_project_id = state.candidate_projects[idx0].id

        # If still None, try fuzzy match by name
        if not state.selected_project_id and project_name:
            pname_lower = project_name.lower()
            for p in state.candidate_projects:
                if p.name.lower() in pname_lower or pname_lower in p.name.lower():
                    state.selected_project_id = p.id
                    break

    # -------------------------------------------
    # 3) Update lead_info (name + email) from extracted info
    # -------------------------------------------
    if extracted:
        email = extracted.get("email")
        if (not state.lead_info.email) and isinstance(email, str) and "@" in email:
            state.lead_info.email = email

        first_name = extracted.get("first_name")
        if (not state.lead_info.first_name) and isinstance(first_name, str) and first_name.strip():
            state.lead_info.first_name = first_name.strip()

    # -------------------------------------------
    # 4) Decide what is still missing and ask accordingly
    # -------------------------------------------

    # 4a) Missing project selection
    if not state.selected_project_id:
        if state.candidate_projects:
            lines = ["Great! To book a visit, which project would you like to see?"]
            for idx, p in enumerate(state.candidate_projects, start=1):
                lines.append(f"{idx}. {p.name} in {p.city}, {p.country}")
            lines.append("You can reply with the project number or the project name.")
            state.messages.append({"role": "assistant", "content": "\n".join(lines)})
        else:
            state.messages.append({
                "role": "assistant",
                "content": "Which project would you like to book a visit for? Please mention the project name."
            })
        state.stage = "booking_need_project"
        return state

    # 4b) Missing contact info (name and/or email)
    need_name = not state.lead_info.first_name
    need_email = not state.lead_info.email

    if need_name and need_email:
        state.messages.append({
            "role": "assistant",
            "content": "Nice choice! To confirm your visit, could you please share your full name and email address?"
        })
        state.stage = "booking_need_contact"
        return state

    if need_email:
        state.messages.append({
            "role": "assistant",
            "content": "Got it! Please share your email address so we can send you the visit confirmation."
        })
        state.stage = "booking_need_contact"
        return state

    if need_name:
        state.messages.append({
            "role": "assistant",
            "content": "Thanks! Lastly, may I know your name for the booking?"
        })
        state.stage = "booking_need_contact"
        return state

    # -------------------------------------------
    # 5) We have project_id + name + email → create booking
    # -------------------------------------------
    booking = create_lead_and_booking(
        lead_info=state.lead_info,
        buyer_profile=state.buyer_profile,
        project_id=state.selected_project_id,
    )

    if booking is None:
        state.messages.append({
            "role": "assistant",
            "content": "I couldn't find that project in our system. Could you please recheck the project details?"
        })
        state.stage = "booking_error"
        return state

    confirmation = (
        f"Perfect, {booking.lead.first_name or 'there'}! 🎉 "
        f"I've created a visit request for **{booking.project.name}** in {booking.city}. "
        f"Our team will reach out to you shortly at **{booking.lead.email}** to confirm the schedule."
    )
    state.messages.append({"role": "assistant", "content": confirmation})
    state.stage = "booking_confirmed"
    return state


def respond_node(state: AgentState) -> AgentState:
    """
    Fallback node: use the LLM to respond generically (no DB/tool call),
    with strong guardrails against hallucinating property details.
    """

    system_prompt = """
You are SilverLand's real-estate assistant.

Guardrails:
- Do NOT invent or guess specific project details (such as exact prices, availability,
  completion dates, floor plans, unit counts, or developer names) if they are not
  explicitly provided in the conversation context.
- If the user asks for project-specific details that you do not see in the messages
  or that must come from the database, say clearly that you don't have that information
  and suggest they ask for:
    - recommendations,
    - general guidance (e.g., how to choose a project),
    - or ask the assistant to "show projects" again.
- For general real-estate advice (e.g., "what to consider when buying in Dubai?",
  "pros and cons of off-plan"), you may answer normally based on your knowledge.
- Never fabricate database-backed facts. When in doubt, say:
  "I don't have that specific information in my data, but here's what I can tell you generally..."

Tone:
- Be clear, concise, and helpful.
- Keep answers grounded and honest, especially when you're unsure.
""".strip()

    # Prepend system message to the conversation
    messages = [{"role": "system", "content": system_prompt}] + state.messages

    reply = llm.chat(messages)
    state.messages.append({"role": "assistant", "content": reply})
    state.stage = "generic"
    return state



def build_graph() -> StateGraph:
    """
    Build and return a LangGraph StateGraph using AgentState.

    Flow per turn:
      user_input_node
        -> intent_classification_node
        -> router_node (via add_conditional_edges)
          -> clarify_prefs_node OR t2sql_node OR booking_node OR project_detail_node OR respond_node
          -> END
    """

    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("user_input_node", user_input_node)
    graph.add_node("intent_classification_node", intent_classification_node)
    graph.add_node("clarify_prefs_node", clarify_prefs_node)
    graph.add_node("t2sql_node", t2sql_node)
    graph.add_node("project_detail_node", project_detail_node)
    graph.add_node("booking_node", booking_node)
    graph.add_node("respond_node", respond_node)

    # Entry point
    graph.set_entry_point("user_input_node")

    # Linear edge from entry to intent classification
    graph.add_edge("user_input_node", "intent_classification_node")

    # Conditional routing based on router_node
    graph.add_conditional_edges(
        "intent_classification_node",
        router_node,
        {
            "clarify_prefs_node": "clarify_prefs_node",
            "t2sql_node": "t2sql_node",
            "booking_node": "booking_node",
            "project_detail_node": "project_detail_node",
            "respond_node": "respond_node",
        },
    )

    # Leaf nodes end the run
    graph.add_edge("clarify_prefs_node", END)
    graph.add_edge("t2sql_node", END)
    graph.add_edge("project_detail_node", END)
    graph.add_edge("booking_node", END)
    graph.add_edge("respond_node", END)

    return graph
