# 🚀 SilverLand AI – Real Estate Assistant

### _AI Engineer Challenge Submission_

An AI-powered real-estate assistant that helps users:

- Provide buying preferences (city, budget, BHK, property type)
- Get relevant project recommendations from a relational database
- Ask questions and see detailed project information
- Book property visits (primary business goal)
- Provide structured conversations using LangGraph

Backend built with:  
**Django + Django Ninja + LangGraph + GPT-4o (via OpenRouter)**

---

# 📌 **1. Tech Stack**

- **Python** 3.11+
- **Django 4.2**
- **Django Ninja** (REST)
- **LangGraph** (agent orchestration)
- **OpenRouter GPT-4o**
- **SQLite** (local) / Any relational DB
- **ORM-based SQL Tool** (extendable to Vanna + ChromaDB)
- **Optional Web Search Tool** (external API)

---

# 📂 **2. Project Structure**

```
silver_land_ai/
  manage.py
  silver_land_ai/
  properties/
    models.py
    admin.py
    management/commands/import_projects.py
  agent/
    state.py
    llm_client.py
    langgraph_graph.py
    tools/
      t2sql_tool.py
      booking_tool.py
      project_info_tool.py
      web_search_tool.py
  api_layer/
    endpoints/
      conversations.py
      agents.py
  README.md
```

---

# 🏗 **3. Models Overview**

## **Project**

Represents real-estate projects with full details (aligned with challenge CSV).

## **Lead**

Stores buyer contact details + extracted preferences.

## **Booking**

Stored in the **required table name**: `visit_bookings`.

- lead
- project
- city
- preferred_date (optional)
- status (pending/confirmed)

## **ConversationSession**

Persists full LangGraph AgentState for each conversation.

---

# 🔧 **4. Setup & Installation**

## 4.1 Create Virtual Environment

```
python -m venv venv
source venv/bin/activate
```

## 4.2 Install Requirements

```
pip install -r requirements.txt
```

## 4.3 Environment Variables

Create `.env` or export these:

```
OPENROUTER_API_KEY=your_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-4o-mini
WEB_SEARCH_API_URL=   # optional
```

## 4.4 Run Migrations

```
python manage.py migrate
```

## 4.5 Import Project Dataset

```
python manage.py import_projects path/to/properties.csv
```

## 4.6 Start Server

```
python manage.py runserver
```

Admin Panel:  
`http://127.0.0.1:8000/admin/`

---

# 💬 **5. API Endpoints**

## **POST /api/conversations**

Starts a new assistant session.

**Response Example:**

```json
{
  "conversation_id": "8100e73d-da85-4a87-844e-689b22483149",
  "message": "Hello! 👋 I'm your SilverLand Property Assistant. Which city are you looking to buy in?"
}
```

---

## **POST /api/agents/chat**

Main chat endpoint.

**Request Example:**

```json
{
  "conversation_id": "8100e73d-da85-4a87-844e-689b22483149",
  "message": "I want a 2 BHK apartment in Dubai under 300000 USD"
}
```

**Response Shape:**

```json
{
  "reply": "Here are some projects matching your preferences...",
  "shortlisted_projects": [...],
  "agent_state": { ... }
}
```

---

# 🧠 **6. Agent Architecture (LangGraph)**

## **State (AgentState)**

Includes:

- messages
- buyer_profile
- candidate_projects
- selected_project_id
- lead_info (name/email)
- intent
- stage

---

## **Nodes in LangGraph**

### **1️⃣ intent_classification_node**

Extracts:

- intent (`prefs`, `book`, `detail`, `generic`)
- city, budget, BHK, property_type
- early lead info (name/email)
- strict JSON schema

---

### **2️⃣ router_node**

Routes to:

- clarify_prefs_node
- t2sql_node
- booking_node
- project_detail_node
- respond_node

---

### **3️⃣ clarify_prefs_node**

Asks for missing:

- city
- unit size / bedrooms
- budget

---

### **4️⃣ t2sql_node (SQL Tool)**

Uses `ProjectSqlTool.search_projects_by_profile()`.

Search logic:

- Hard filters: city, bedrooms, property_type
- Soft filters: unit_size, budget
- Budget fallback
- Returns `ProjectSummary` list

---

### **5️⃣ project_detail_node**

Understands:

- "first project", "project 2", "any project"

Fetches:

- features
- facilities
- price
- unit type
- completion status
- description

Fallback to WebSearchTool if DB lacks details.

---

### **6️⃣ booking_node**

Booking flow using GPT extraction:

Extracts:

- project_index / project_name
- name
- email

Asks sequentially for missing details.  
Creates `Lead` + `Booking` → stored in `visit_bookings`.

---

### **7️⃣ respond_node**

Fallback safe responder with **no hallucination guardrails**.

---

# 🛠 **7. Tools**

## **ProjectSqlTool**

- ORM-based SQL tool
- Future-ready for Vanna + ChromaDB
- Includes placeholder `text_to_sql`

---

## **WebSearchTool**

Optional tool activated if `WEB_SEARCH_API_URL` is provided.

Used when DB lacks project details.

---

# 🧪 **8. Testing Strategy**

Recommended tests:

- test_intent_classification
- test_project_search
- test_booking_flow
- test_project_detail_fallback
- test_full_conversation

---

# 📝 **9. Requirement Checklist**

### ✔ Preference collection

### ✔ Recommendations

### ✔ Detailed project lookup

### ✔ Booking flow + stored in `visit_bookings`

### ✔ Session-based LangGraph agent

### ✔ SQL tool abstraction

### ✔ Optional web search

### ✔ Guardrails for hallucination

### ✔ REST API + DB-backed state

---

# 🌟 **10. Future Extensions**

- Vanna + ChromaDB
- Real-time web search
- Next.js chat UI
- Deployment container
- Analytics dashboard

---

# 🎉 End of README
