import spacy
import hashlib
from db import get_messages

nlp = spacy.load("en_core_web_sm")

prompt_cache = {}


def extract_named_entities(text):
    """Extract named entities like people, places, organizations."""
    doc = nlp(text)
    return [ent.text for ent in doc.ents if ent.label_ in ['GPE', 'LOC', 'ORG', 'PERSON']]

def classify_query_type(text):
    """Classify the type of query for tone adjustment."""
    text = text.lower()
    if text.startswith("what is") or text.startswith("define"):
        return "definition"
    elif text.startswith("how") or "steps" in text:
        return "how_to"
    elif "summarize" in text or "summary" in text:
        return "summary"
    elif "why" in text:
        return "reasoning"
    else:
        return "general"

def hash_prompt(prompt):
    """Hash the prompt to cache it efficiently."""
    return hashlib.md5(prompt.strip().lower().encode()).hexdigest()

def get_latest_user_context(session_id, max_lookback=5):
    """
    Look back through recent user messages to extract the most recent named entity.
    This prevents older topics from affecting newer ones.
    """

    messages = get_messages(session_id)
    recent_entities = []
    seen = set()
    count = 0

    for msg in reversed(messages):
        if msg["role"] != "user":
            continue
        entities = extract_named_entities(msg["content"])
        for ent in entities:
            if ent not in seen:
                recent_entities.append(ent)
                seen.add(ent)
        count += 1
        if count >= max_lookback:
            break

    return recent_entities

def generate_contextual_prompt(session_id, current_prompt):
    """
    Generate a full system prompt based on the query type, previous chat context,
    and current user prompt.
    """
    #it will give content
    prompt_hash = hash_prompt(current_prompt)
    if prompt_hash in prompt_cache:
        return prompt_cache[prompt_hash]

    query_type = classify_query_type(current_prompt)
    context_entities = get_latest_user_context(session_id)

    system_instruction = "You are an insightful and fast AI assistant. Always prioritize clarity, brevity, and natural conversation.\n"

    if query_type == "definition":
        system_instruction += "Define the term clearly. Use plain English, like you're teaching someone casually.\n"
    elif query_type == "how_to":
        system_instruction += "Explain steps logically in bullet points. Use helpful examples if possible.\n"
    elif query_type == "summary":
        system_instruction += "Summarize the key points simply, like you're recapping a meeting for a friend.\n"
    elif query_type == "reasoning":
        system_instruction += "Give the main reason clearly. Contrast if needed, but stay concise.\n"
    else:
        system_instruction += "Answer naturally. Be conversational, but avoid fluff. Contrast ideas where useful.\n"

    context_line = f"Earlier, we discussed: {', '.join(context_entities)}.\n" if context_entities else ""

    full_prompt = f"{system_instruction}{context_line}User: {current_prompt.strip()}\nAssistant:"

    prompt_cache[prompt_hash] = full_prompt
    return full_prompt
