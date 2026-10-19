"""
Meeting summary service - generates summaries from transcripts.
"""

from app.ai.gateway import generate_ai_response


async def generate_meeting_summary(
    transcript: str,
    provider: str = "ollama",
    model: str | None = None,
    custom_api_base_url: str | None = None,
    custom_api_key: str | None = None,
) -> tuple[str, str]:
    """
    Generate a summary from meeting transcript.
    
    Args:
        transcript: The meeting transcript text
        provider: AI provider ("openai", "ollama", or "custom")
        model: Specific model to use (optional)
    
    Returns:
        Summary text
    """
    messages = [
        {
            "role": "system",
            "content": """You are a professional meeting summarization assistant. 
Generate a concise, well-structured summary including:
1. Meeting topic/purpose
2. Key discussion points
3. Decisions made
4. Action items with owners
5. Next steps

Keep it under 500 words. Use bullet points where appropriate."""
        },
        {
            "role": "user",
            "content": f"Please summarize this meeting transcript:\n\n{transcript}"
        }
    ]
    
    summary, used_model = await generate_ai_response(
        provider=provider,
        messages=messages,
        model=model,
        custom_api_base_url=custom_api_base_url,
        custom_api_key=custom_api_key,
    )

    return summary, used_model


async def extract_action_items(transcript: str) -> list[str]:
    """Extract action items from transcript."""
    messages = [
        {
            "role": "system",
            "content": "Extract all action items from the meeting transcript. Return as a numbered list."
        },
        {
            "role": "user",
            "content": f"Meeting transcript:\n\n{transcript}"
        }
    ]
    
    response, _ = await generate_ai_response(
        provider="ollama",
        messages=messages,
    )
    
    return response.split("\n")
