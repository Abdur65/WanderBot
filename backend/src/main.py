from langgraph.types import Command
from src.graph import graph
from src.config import GROQ_MODEL
import uuid

def export_itinerary(draft: str, destination: str):
    filename = f"itinerary_{destination.lower().replace(' ', '_')}.md"
    with open(filename, "w") as f:
        f.write(f"# Travel Itinerary — {destination}\n\n")
        f.write(draft)
    print(f"\n✅ Itinerary exported to {filename}")

def run():
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("=" * 50)
    print("  Travel Itinerary Planning Assistant")
    print(f"  Model: {GROQ_MODEL}")
    print("=" * 50)

    user_input = input("\nWhere would you like to travel? (be descriptive)\n> ").strip()
    if not user_input:
        print("No input provided. Exiting.")
        return

    initial_state = {
        "messages": [{"role": "user", "content": user_input}],
        "destination": "",
        "context": "",
        "draft_itinerary": "",
        "tavily_calls": 0,
        "knowledge_ready": False,
        "verification_score": 0.0,
    }

    print("\n🔍 Agent is researching your trip...\n")

    # First run: streams through analyze → curate → rag → verify → draft → human_review
    # Graph suspends at interrupt() inside human_review
    for event in graph.stream(initial_state, config, stream_mode="values"):
        pass

    # Review loop: resume from interrupt each iteration via Command(resume=)
    while True:
        state = graph.get_state(config)

        # No pending interrupts means graph reached END (user approved)
        if not state.interrupts:
            draft = state.values.get("draft_itinerary", "")
            destination = state.values.get("destination", "destination")
            export_itinerary(draft, destination)
            break

        # The interrupt value is the dict passed to interrupt() in human_review
        draft = state.interrupts[0].value.get("draft_itinerary", "")

        print("\n" + "=" * 50)
        print(draft)
        print("=" * 50)

        feedback = input("\n> Type 'approve' to export, or give feedback to refine: ").strip()

        print(f"\n♻️  Refining based on: '{feedback}'\n")

        # Resume the suspended interrupt() call with the user's feedback string.
        # human_review stores it in messages; route_after_review reads messages[-1].
        for event in graph.stream(Command(resume=feedback), config, stream_mode="values"):
            pass

if __name__ == "__main__":
    run()