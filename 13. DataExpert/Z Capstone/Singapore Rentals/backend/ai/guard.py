"""
Input guard middleware for Casota AI chat.
Runs two checks before the main Claude stream:
  1. Profanity — keyword list, instant
  2. Relevance — lightweight Claude classification call
"""

import re
from dataclasses import dataclass

import anthropic

_PROFANITY: set[str] = {
    "fuck", "shit", "cunt", "bitch", "asshole", "bastard", "motherfucker",
    "dickhead", "prick", "twat", "wanker", "cock", "whore", "slut", "fag",
    "faggot", "nigger", "nigga", "chink", "spic", "kike", "retard",
}

_WORD_RE = re.compile(r"\b\w+\b")


@dataclass
class GuardResult:
    blocked: bool
    reply: str = ""


def _has_profanity(text: str) -> bool:
    return any(w in _PROFANITY for w in _WORD_RE.findall(text.lower()))


async def run_guard(message: str, client: anthropic.AsyncAnthropic) -> GuardResult:
    if _has_profanity(message):
        return GuardResult(
            blocked=True,
            reply="Please keep the conversation respectful — I'm here to help with Singapore rentals.",
        )

    relevant = await _is_relevant(message, client)
    if not relevant:
        return GuardResult(
            blocked=True,
            reply=(
                "I'm focused on Singapore's private residential rental market. "
                "Ask me about rents, buildings, districts, MRT proximity, price trends, or rental deals!"
            ),
        )

    return GuardResult(blocked=False)


async def _is_relevant(message: str, client: anthropic.AsyncAnthropic) -> bool:
    """
    Quick binary classification: is this message relevant to Singapore rentals?
    Uses max_tokens=3 — expects 'yes' or 'no'.
    """
    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3,
            system=(
                "You are a relevance classifier. Reply ONLY with 'yes' or 'no'.\n"
                "Answer 'yes' if the message is related to any of: Singapore property rentals, "
                "housing, condos, apartments, districts, MRT stations, rent prices, lease data, "
                "real estate trends, building names, neighbourhoods, or general Singapore geography.\n"
                "Answer 'no' for everything else (politics, coding help, jokes, personal advice, etc.)."
            ),
            messages=[{"role": "user", "content": message}],
        )
        answer = resp.content[0].text.strip().lower()
        return answer.startswith("y")
    except Exception:
        # On any API error, allow the message through rather than blocking valid users
        return True
