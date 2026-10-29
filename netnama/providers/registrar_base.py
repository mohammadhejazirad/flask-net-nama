from typing import Protocol


class RegistrarAdapter(Protocol):
    """Optional real registrar integration; base release requires no API key."""

    async def availability(self, domain: str) -> dict: ...
