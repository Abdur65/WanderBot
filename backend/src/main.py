from src.graph import graph
from src.config import GROQ_MODEL
import uuid
import json

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
    }
    
    print("\n🔍 Agent is researching your trip...\n")
    
    # Run until the first interrupt (human_review node)
    for event in graph.stream(initial_state, config, stream_mode="values"):
        pass  # nodes print their own progress logs
    
    # Loop: show draft → get feedback → re-run or export
    while True:
        state = graph.get_state(config)
        draft = state.values.get("draft_itinerary", "")
        destination = state.values.get("destination", "destination")
        
        print("\n" + "=" * 50)
        print(draft)
        print("=" * 50)
        
        feedback = input("\n> Type 'approve' to export, or give feedback to refine: ").strip()
        
        if feedback.lower() == "approve":
            export_itinerary(draft, destination)
            break
        
        print(f"\n♻️  Refining based on: '{feedback}'\n")
        
        # Resume the graph with the user's feedback
        for event in graph.stream(
            {"messages": [{"role": "user", "content": feedback}]},
            config,
            stream_mode="values"
        ):
            pass

if __name__ == "__main__":
    run()