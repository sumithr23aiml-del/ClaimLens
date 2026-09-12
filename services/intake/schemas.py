from pydantic import BaseModel, Field
from typing import List


class ClaimImageInput(BaseModel):
    slot: str
    path: str


class ClaimCreate(BaseModel):
    policy_id: str
    description: str
    images: List[ClaimImageInput] = Field(default_factory=list)