from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from src.config import GROQ_API_KEY, GROQ_MODEL
from src.state import AgentState, Preferences

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)
structured_llm = llm.with_structured_output(Preferences)

# Separate schema + chain for reliable destination extraction
class TripInfo(BaseModel):
    destination: str  # full place name as stated, e.g. "Tokyo, Japan" or "Paris"

DESTINATION_SYSTEM = """
Extract the travel destination from the user's message.
Return the full place name exactly as the user stated it (e.g. "Tokyo, Japan",
"Paris", "Kyoto", "New York City"). Do not abbreviate or alter it.
If no destination is mentioned, return an empty string.
"""

destination_chain = (
    ChatPromptTemplate.from_messages([
        ("system", DESTINATION_SYSTEM),
        ("human", "{input}"),
    ])
    | llm.with_structured_output(TripInfo)
)

SYSTEM = """
You are the intake agent for WanderBot, an AI travel planning assistant.
Your sole responsibility is to extract the travel destination and user preferences
from the full conversation history provided.

EXTRACTION RULES:
- Read the entire conversation carefully before extracting — the user may have
  updated or corrected a preference in a later message.
- The most recently stated value for any field always takes priority over earlier
  values.
- Never reset a field to its default if the user previously stated a value for it
  and has not explicitly changed it in this conversation.
- If a field is not mentioned anywhere in the conversation, use its default value.
- Do not infer or assume values the user has not expressed. Only extract what was
  explicitly stated.

FIELD GUIDANCE:

budget:
  "budget", "cheap", "affordable", "backpacker", "tight budget" → "budget"
  "mid-range", "moderate", "reasonable", "comfortable" → "mid"
  "luxury", "splurge", "high-end", "premium", "no expense spared" → "luxury"
  If not mentioned → default "mid"

pace:
  "relaxed", "slow", "leisurely", "easy", "plenty of rest" → "slow"
  "balanced", "moderate", "mix of activity and rest" → "moderate"
  "packed", "fast", "as much as possible", "action-packed" → "fast"
  If not mentioned → default "moderate"

interests:
  Extract all activities, themes, and topics the user expresses interest in.
  Examples: ["street food", "architecture", "jazz", "hiking", "museums", "nightlife"]
  Capture the user's exact phrasing where possible.
  If not mentioned → empty list []

dietary:
  Extract all dietary requirements, restrictions, and preferences.
  Examples: ["vegan", "vegetarian", "gluten-free", "halal", "kosher", "nut allergy"]
  If not mentioned → empty list []

mobility:
  "walk", "on foot", "walking everywhere" → "walking"
  "drive", "car", "taxi", "uber" → "driving"
  "public transport", "metro", "bus", "transit", "train" → "transit"
  If not mentioned → default "transit"

duration_days:
  Extract the number of days explicitly stated.
  "a week" → 7, "long weekend" → 3, "10 days" → 10
  If not mentioned → null

travel_party:
  "solo", "by myself", "alone", "just me" → "solo"
  "couple", "partner", "wife", "husband", "anniversary", "honeymoon" → "couple"
  "family", "kids", "children", "parents", "elderly" → "family"
  "group", "friends", "colleagues" → "group"
  If not mentioned → default "solo"

accommodation_area:
  Extract any neighbourhood, district, landmark, or area the user mentions
  as their base or hotel location.
  Examples: "near Shinjuku station", "in the Marais", "close to the city centre"
  If not mentioned → null

must_see:
  Extract any specific places, venues, or experiences the user explicitly says
  they want or need to include.
  Examples: ["Sainte-Chapelle", "Tsukiji Market", "a rooftop bar"]
  If not mentioned → empty list []

avoid:
  Extract any places, venue types, or experiences the user explicitly says
  they want to skip or have already visited.
  Examples: ["Eiffel Tower", "crowded tourist traps", "the Louvre"]
  If not mentioned → empty list []

accessibility:
  Extract any physical constraints, medical needs, or accessibility requirements.
  Examples: ["limited mobility", "no stairs", "wheelchair accessible", "bad knee"]
  If not mentioned → empty list []

OUTPUT:
Return a valid Preferences object with all fields populated according to the rules
above. Do not include any explanation or commentary — structured output only.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "{input}")
])

chain = prompt | structured_llm

def analyze_request(state: AgentState) -> dict:
    last_message = state["messages"][-1].content

    # LLM-based destination extraction — handles multi-word places correctly
    trip_info = destination_chain.invoke({"input": last_message})
    destination = trip_info.destination.strip() or last_message.strip().title()

    preferences = chain.invoke({"input": last_message})

    print(f"[Analyze] Destination: {destination}")
    print(f"[Analyze] Preferences: {preferences}")

    return {
        "destination": destination,
        "preferences": preferences,
        "knowledge_ready": False,
        "tavily_calls": 0,
        "verification_score": 0.0,
    }