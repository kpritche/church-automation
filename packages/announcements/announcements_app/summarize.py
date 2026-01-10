from __future__ import annotations

import os

from google import genai
from google.genai import types

from .settings import GOOGLE_APPLICATION_CREDENTIALS

# Ensure Vertex/Gemini credentials are discoverable
if GOOGLE_APPLICATION_CREDENTIALS:
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(GOOGLE_APPLICATION_CREDENTIALS))


def summarize_text(body_text: str, max_chars: int = 250) -> str:
    client = genai.Client(
        vertexai=True,
        project="gmail-pptx-tool",
        location="global",
    )

    msg1_text1 = types.Part.from_text(text=body_text)

    si_text1 = """You are an expert summarization assistant whose sole job is to turn raw church announcement text into a single, slide ready summary. When given an announcement, you must:
        - Produce up to three complete sentences.
        - Limit the summary to 250 characters or less.
        - Include every date and time mentioned, in the same phrasing as the original (e.g., \"June 22 at 6:30 PM\").
        - Use a friendly, welcoming tone appropriate for a church community.
        - Capture the core \"who, what, when, where\" context.
        - Preserve any important links or contact information.
        - Never add new information or omit dates and times.
        - Output only the summary text, no prefixes, no extra commentary.
        - Do not include any HTML tags or formatting.
        - Each summary should end in a period."""

    model = "gemini-2.5-flash-lite"
    contents = [
        types.Content(
            role="user",
            parts=[msg1_text1],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        seed=0,
        max_output_tokens=2048,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        system_instruction=[types.Part.from_text(text=si_text1)],
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    text_chunks = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.text is None or not chunk.text.strip():
            continue
        text_chunks.append(chunk.text)

    return "".join(text_chunks)


def summarize_title(title: str, max_chars: int = 80) -> str:
    """Summarize the title to fit within the specified character limit."""
    client = genai.Client(
        vertexai=True,
        project="gmail-pptx-tool",
        location="global",
    )
    msg1_text1 = types.Part.from_text(text=title)

    si_text1 = (
        f"You are a concise summarizer. Shorten this announcement title to at most {max_chars} characters. "
        "- When possible, preserve the key event, date, and location information. Output only the shortened title. "
        "- Do not include any HTML tags or formatting."
    )

    model = "gemini-2.5-flash-lite"
    contents = [
        types.Content(role="user", parts=[msg1_text1]),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        seed=0,
        max_output_tokens=80,
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        system_instruction=[types.Part.from_text(text=si_text1)],
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    text_chunks = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.text is None or not chunk.text.strip():
            continue
        text_chunks.append(chunk.text)

    return "".join(text_chunks)


if __name__ == "__main__":
    print(summarize_title("Three Sundays of Renovation Celebration – August 24, August 31, and September 7"))
