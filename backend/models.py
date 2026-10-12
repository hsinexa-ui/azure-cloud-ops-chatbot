"""Pydantic request and response models for the API."""

from typing import Optional

from pydantic import BaseModel, Field


class OperationResponse(BaseModel):
    success: bool
    message: str
    vm_name: Optional[str] = None
    status: Optional[str] = None
    requires_confirmation: bool = False


class StopRequest(BaseModel):
    confirmed: bool = Field(
        default=False,
        description="Must be true to deallocate the configured development/test VM.",
    )


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    confirmed: Optional[bool] = Field(
        default=None,
        description="Optional explicit confirmation for a pending stop request.",
    )


class ChatResponse(BaseModel):
    success: bool
    reply: str
    action: Optional[str] = None
    requires_confirmation: bool = False
    vm_name: Optional[str] = None
    status: Optional[str] = None
