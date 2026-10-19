from app.core.config import get_settings


class AIProviderError(RuntimeError):
    pass


async def generate_gemini_response(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str]:
    settings = get_settings()
    selected_api_key = api_key or settings.gemini_api_key

    if not selected_api_key:
        raise AIProviderError("Provide your Gemini API key or configure DEVNEXUS_GEMINI_API_KEY.")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise AIProviderError("Install Gemini dependency with: python -m pip install google-genai") from exc

    system_instruction = "\n\n".join(
        message["content"] for message in messages if message["role"] == "system"
    ) or None
    contents = [
        {
            "role": "model" if message["role"] == "assistant" else "user",
            "parts": [{"text": message["content"]}],
        }
        for message in messages
        if message["role"] != "system"
    ]
    selected_model = model or settings.gemini_model
    client = genai.Client(api_key=selected_api_key)

    try:
        response = await client.aio.models.generate_content(
            model=selected_model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
        )
    except Exception as exc:
        raise AIProviderError("Gemini request failed. Check the API key, model, and network connection.") from exc

    assistant_content = response.text
    if not assistant_content:
        raise AIProviderError("Gemini returned an empty response.")

    return assistant_content, selected_model


async def generate_openai_response(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str]:
    settings = get_settings()

    selected_api_key = api_key or settings.openai_api_key
    if not selected_api_key:
        raise AIProviderError("Provide your OpenAI API key or configure DEVNEXUS_OPENAI_API_KEY.")

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise AIProviderError("Install OpenAI dependency with: python -m pip install openai") from exc

    selected_model = model or settings.openai_model
    client = AsyncOpenAI(api_key=selected_api_key)
    response = await client.chat.completions.create(
        model=selected_model,
        messages=messages,
    )

    assistant_content = response.choices[0].message.content
    if not assistant_content:
        raise AIProviderError("AI provider returned an empty response.")

    return assistant_content, selected_model


async def generate_custom_api_response(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str]:
    settings = get_settings()
    selected_base_url = base_url or settings.custom_api_base_url

    if not selected_base_url:
        raise AIProviderError("Enter a Custom API URL or configure DEVNEXUS_CUSTOM_API_BASE_URL.")

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise AIProviderError("Install OpenAI dependency with: python -m pip install openai") from exc

    selected_model = model or settings.custom_api_model
    if not selected_model:
        raise AIProviderError("Set DEVNEXUS_CUSTOM_API_MODEL or choose a chat model.")

    client = AsyncOpenAI(
        base_url=selected_base_url,
        api_key=api_key or settings.custom_api_key or "not-needed",
    )
    try:
        response = await client.chat.completions.create(
            model=selected_model,
            messages=messages,
        )
    except Exception as exc:
        raise AIProviderError(
            "Custom API request failed. Check the API URL, API key, model, and network connection."
        ) from exc

    assistant_content = response.choices[0].message.content
    if not assistant_content:
        raise AIProviderError("Custom API returned an empty response.")

    return assistant_content, selected_model


async def list_custom_api_models(
    *,
    base_url: str,
    api_key: str | None = None,
) -> list[str]:
    settings = get_settings()

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise AIProviderError("Install OpenAI dependency with: python -m pip install openai") from exc

    try:
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or settings.custom_api_key or "not-needed",
            timeout=20.0,
        )
        response = await client.models.list()
    except Exception as exc:
        raise AIProviderError(
            "Could not load models from the Custom API. Check the URL, API key, and provider compatibility."
        ) from exc

    return sorted({item.id for item in response.data if item.id})


async def generate_ollama_response(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
) -> tuple[str, str]:
    settings = get_settings()

    try:
        from ollama import AsyncClient
    except ImportError as exc:
        raise AIProviderError("Install Ollama dependency with: python -m pip install ollama") from exc

    selected_model = model or settings.ollama_model
    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"

    client = AsyncClient(host=settings.ollama_host, headers=headers or None)
    try:
        response = await client.chat(
            model=selected_model,
            messages=messages,
        )
    except Exception as exc:
        raise AIProviderError(
            "Ollama request failed. Make sure Ollama is running and the model is available."
        ) from exc

    assistant_content = response.message.content
    if not assistant_content:
        raise AIProviderError("Ollama returned an empty response.")

    return assistant_content, selected_model


async def generate_ai_response(
    *,
    provider: str,
    messages: list[dict[str, str]],
    model: str | None = None,
    custom_api_base_url: str | None = None,
    custom_api_key: str | None = None,
    openai_api_key: str | None = None,
    gemini_api_key: str | None = None,
) -> tuple[str, str]:
    if provider == "gemini":
        return await generate_gemini_response(
            messages=messages,
            model=model,
            api_key=gemini_api_key,
        )

    if provider == "openai":
        return await generate_openai_response(messages=messages, model=model, api_key=openai_api_key)

    if provider == "custom":
        return await generate_custom_api_response(
            messages=messages,
            model=model,
            base_url=custom_api_base_url,
            api_key=custom_api_key,
        )

    if provider == "ollama":
        return await generate_ollama_response(messages=messages, model=model)

    raise AIProviderError(f"Unsupported AI provider: {provider}")
