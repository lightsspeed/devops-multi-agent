from typing import Literal

from pydantic import BaseModel


class RoutingDecision(BaseModel):
    agent: Literal["kubernetes", "aws", "linux"]
    reason: str