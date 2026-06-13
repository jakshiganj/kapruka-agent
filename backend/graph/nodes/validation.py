from __future__ import annotations



from typing import Any



from graph.state import AgentState

from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_check_delivery, resolve_delivery_city





def validation_node(state: AgentState) -> dict[str, Any]:

    cart = state.get("cart") or []

    delivery_info = dict(state.get("delivery_info") or {})

    ui_payload = dict((state.get("ui_action") or {}).get("payload") or {})



    if not cart:

        return {

            "voice_prompt": "Your cart is empty. What would you like to order?",

            "next_node": "discovery",

        }



    city_input = delivery_info.get("city")

    delivery_date = delivery_info.get("date")

    if not city_input or not delivery_date:

        return {

            "voice_prompt": "Please tell me the delivery city and date.",

            "next_node": "end",

        }



    try:

        canonical_city = resolve_delivery_city(city_input)

    except KaprukaMCPError as exc:

        message = str(exc).removeprefix("Error:").strip()

        delivery_info["validated"] = "false"

        return {

            "delivery_info": delivery_info,

            "ui_action": {

                "action": "update_cart",

                "payload": {**ui_payload, "cart": cart, "delivery_info": delivery_info},

            },

            "voice_prompt": (

                "I couldn't verify delivery for that city. "

                f"{message} Please check the city name and try again."

            ),

            "next_node": "end",

        }



    warnings: list[str] = []

    last_rate: str | None = None



    for item in cart:

        try:

            check = kapruka_check_delivery(

                city=canonical_city,

                delivery_date=delivery_date,

                product_id=item["product_id"],

            )

        except KaprukaMCPError as exc:

            message = str(exc).removeprefix("Error:").strip()

            delivery_info["validated"] = "false"

            return {

                "delivery_info": delivery_info,

                "ui_action": {

                    "action": "update_cart",

                    "payload": {**ui_payload, "cart": cart, "delivery_info": delivery_info},

                },

                "voice_prompt": (

                    f"I couldn't check delivery for {item.get('name', 'an item')}. {message}"

                ),

                "next_node": "end",

            }



        if not check.get("available"):

            reason = check.get("reason") or "Delivery is not available for that date."

            next_date = check.get("next_available_date")

            delivery_info["city"] = canonical_city

            delivery_info["validated"] = "false"

            prompt = (

                f"Delivery of {item.get('name', 'one item')} to {canonical_city} "

                f"on {delivery_date} isn't available. {reason}"

            )

            if next_date:

                prompt += f" The next available date is {next_date}."

            return {

                "delivery_info": delivery_info,

                "ui_action": {

                    "action": "update_cart",

                    "payload": {**ui_payload, "cart": cart, "delivery_info": delivery_info},

                },

                "voice_prompt": prompt,

                "next_node": "end",

            }



        if check.get("perishable_warning"):

            warnings.append(str(check["perishable_warning"]))

        if check.get("rate") is not None:

            last_rate = str(check["rate"])



    delivery_info["city"] = canonical_city

    delivery_info["validated"] = "true"

    delivery_info["delivery_rate"] = last_rate or delivery_info.get("delivery_rate", "")



    prompt = (

        f"Good news — delivery to {canonical_city} on {delivery_date} is available "

        f"for LKR {last_rate} flat rate for your {len(cart)} item cart. "

        f"Your order is NOT placed yet — when you checkout, give me the recipient name, "

        f"phone, street address, your name as sender, and an optional gift message."

    )

    if warnings:

        prompt += f" Note: {' '.join(dict.fromkeys(warnings))}"



    return {

        "delivery_info": delivery_info,

        "ui_action": {

            "action": "update_cart",

            "payload": {**ui_payload, "cart": cart, "delivery_info": delivery_info},

        },

        "voice_prompt": prompt,

        "next_node": "end",

    }


