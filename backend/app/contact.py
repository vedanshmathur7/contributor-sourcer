"""Contact rule (TC4): the only permitted source is the profile's public email field.

Never derived from commit metadata, never pattern-guessed (first.last@company), never inferred by an LLM.
"""

import re

from app.schemas import Profile

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

NOT_PUBLIC_REASON = (
    "This developer has not made an email public on their profile. "
    "We never guess addresses or harvest them from commit metadata."
)


def resolve_contact(profile: Profile) -> str | None:
    email = (profile.public_email or "").strip()
    return email if _EMAIL.match(email) else None
