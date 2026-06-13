from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    cart: List[Dict[str, Any]]
    delivery_info: Dict[str, str]
    checkout_info: Dict[str, Any]
    ui_action: Dict[str, Any]
    voice_prompt: str
    next_node: str


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
    voice_prompt: str = Field(
        default="",
        description="Short spoken response for the user.",
    )


class NodeOutput(BaseModel):
    ui_action: Dict[str, Any] = Field(default_factory=dict)
    voice_prompt: str = Field(default="")
    next_node: NextNode = Field(default="end")
