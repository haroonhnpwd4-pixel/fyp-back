#!/usr/bin/env python3
"""
Local test for meeting summary module.
Run: python test_meeting_summary.py
"""

import asyncio
from app.ai.gateway import generate_ai_response


async def test_meeting_summary():
    """Test meeting summary generation with sample meeting transcript."""
    
    sample_transcript = """
    John: Let's discuss the Q4 roadmap.
    Sarah: I think we should focus on performance optimization.
    John: Agreed. What's our priority?
    Sarah: Database query optimization and caching strategy.
    Mike: We should also improve API response times.
    John: Good point. Let's allocate 2 sprints for this.
    Sarah: Should we add monitoring dashboards?
    John: Yes, definitely. Mike, can you lead that?
    Mike: Sure, I'll start next week.
    John: Let's wrap up. Action items: DB optimization (Sarah), monitoring (Mike).
    """

    # Create messages for summary generation
    messages = [
        {
            "role": "system",
            "content": "You are a meeting summarization assistant. Generate a concise summary of the meeting including key topics, decisions, and action items."
        },
        {
            "role": "user",
            "content": f"Summarize this meeting transcript:\n\n{sample_transcript}"
        }
    ]

    try:
        # Test with Ollama (local)
        print("Testing with Ollama (local)...")
        summary, model = await generate_ai_response(
            provider="ollama",
            messages=messages,
            model="llama2"  # Change to your local model
        )
        print(f"\n✓ Ollama Summary ({model}):")
        print(summary)
        print("\n" + "="*80 + "\n")

    except Exception as e:
        print(f"✗ Ollama failed: {e}\n")

    try:
        # Test with OpenAI (requires API key)
        print("Testing with OpenAI (requires DEVNEXUS_OPENAI_API_KEY)...")
        summary, model = await generate_ai_response(
            provider="openai",
            messages=messages,
            model="gpt-4"
        )
        print(f"\n✓ OpenAI Summary ({model}):")
        print(summary)

    except Exception as e:
        print(f"✗ OpenAI failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_meeting_summary())
