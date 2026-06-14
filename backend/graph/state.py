from typing import Annotated, Any, Dict, List, Literal, NotRequired, Optional, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


OrderPhase = Literal["shopping", "link_ready", "branch_pending"]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    cart: List[Dict[str, Any]]
    delivery_info: Dict[str, str]
    checkout_info: Dict[str, Any]
    checkout_result: NotRequired[Dict[str, Any]]
    checkout_cart_snapshot: NotRequired[List[Dict[str, Any]]]
    order_phase: NotRequired[OrderPhase]
    post_link_trigger_text: NotRequired[str]
    post_link_pending_query: NotRequired[str]
    ui_action: Dict[str, Any]
    voice_prompt: str
    next_node: str
    voice_mode: NotRequired[bool]


NextNode = Literal["discovery", "cart_manager", "validation", "checkout", "end"]


class RouterDecision(BaseModel):
    next_node: NextNode = Field(
        description="Which graph node to run next."
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Product search query extracted from user intent.",
    )
    delivery_city: Optional[str] = Field(
        default=None,
        description="Delivery city mentioned by the user.",
    )
    delivery_date: Optional[str] = Field(
        default=None,
        description="Delivery date in YYYY-MM-DD format.",
    )
    recipient_name: Optional[str] = Field(
        default=None,
        description="Name of the gift recipient for checkout.",
    )
    recipient_phone: Optional[str] = Field(
        default=None,
        description="Recipient phone number for checkout.",
    )
    recipient_address: Optional[str] = Field(
        default=None,
        description="Recipient street address for delivery (not just the city).",
    )
    sender_name: Optional[str] = Field(
        default=None,
        description="Name of the person sending the gift.",
    )
    gift_message: Optional[str] = Field(
        default=None,
        description="Optional gift message for the order.",
    )
    wants_checkout: bool = Field(
        default=False,
        description="True when the user wants to place/checkout the order now.",
    )
    voice_prompt: str = Field(
        default="",
        description="Short spoken response for the user.",
    )


class NodeOutput(BaseModel):
    ui_action: Dict[str, Any] = Field(default_factory=dict)
    voice_prompt: str = Field(default="")
    next_node: NextNode = Field(default="end")
