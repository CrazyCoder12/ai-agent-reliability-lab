"""Tool boundary with ownership enforcement, business policy, and controlled failures."""

from datetime import date
from typing import Any

from .domain import Fault, ToolEvent, Transport
from .store import NOW, Store


class ToolError(Exception):
    pass


class AccessDenied(ToolError):
    pass


class Unavailable(ToolError):
    pass


class NotFound(ToolError):
    pass


def eligibility(order: dict[str, Any]) -> tuple[bool, str]:
    age = (NOW - date.fromisoformat(order["purchased_on"])).days
    if not order["paid"] or order["cancelled"]:
        return False, "Order must be paid and not cancelled"
    if order["amount"] <= 0:
        return False, "Refund amount must be positive"
    if not 0 <= age <= 30:
        return False, "Refund window is 0–30 calendar days, inclusive"
    return True, "Eligible for a full refund"


class Tools:
    """The principal comes from the trusted runner, never from model arguments.

    The SQLite sandbox executes serially. This demonstrates retry idempotency,
    not distributed or concurrent payment processing.
    """

    def __init__(
        self,
        store: Store,
        principal: str,
        fault: Fault = Fault.NONE,
        transport: Transport = "normal",
        max_calls: int = 20,
    ):
        self.store = store
        self.principal = principal
        self.fault = fault
        self.transport = transport
        self.events: list[ToolEvent] = []
        self.refund_attempts = 0
        self.max_calls = max_calls

    def _owned(self, order_id: str) -> dict[str, Any]:
        order = self.store.order(order_id)
        if order is None:
            raise NotFound("Order not found")
        if order["owner"] != self.principal and self.fault != Fault.AUTH_BYPASS:
            raise AccessDenied("You cannot access this order")
        return order

    def call(self, tool: str, **arguments: Any) -> dict[str, Any]:
        if len(self.events) >= self.max_calls:
            raise ToolError("Tool-call budget exhausted")
        try:
            if set(arguments) != {"order_id"} and not (
                tool == "issue_refund" and set(arguments) == {"order_id", "idempotency_key"}
            ):
                raise ToolError("Invalid tool arguments")
            order_id = arguments.get("order_id")
            if not isinstance(order_id, str):
                raise ToolError("order_id must be a string")
            order = self._owned(order_id)
            if tool == "get_order":
                if self.transport == "lookup_timeout":
                    raise Unavailable("Order lookup timed out")
                result = {"unexpected": True} if self.transport == "malformed" else order
            elif tool == "check_policy":
                allowed, reason = eligibility(order)
                if self.fault == Fault.POLICY_BYPASS:
                    allowed, reason = True, "Policy bypass enabled"
                result = {"eligible": allowed, "reason": reason}
            elif tool == "issue_refund":
                result = self._refund(order, arguments.get("idempotency_key"))
            else:
                raise ToolError("Unknown tool")
        except ToolError as exc:
            self.events.append(
                ToolEvent(
                    sequence=len(self.events) + 1,
                    tool=tool,
                    arguments=arguments,
                    outcome="denied" if isinstance(exc, AccessDenied) else "error",
                    response={"error": type(exc).__name__, "message": str(exc)},
                )
            )
            raise
        self.events.append(
            ToolEvent(
                sequence=len(self.events) + 1,
                tool=tool,
                arguments=arguments,
                outcome="ok",
                response=result,
            )
        )
        return result

    def _refund(self, order: dict[str, Any], key: Any) -> dict[str, Any]:
        if not isinstance(key, str) or not key.strip():
            raise ToolError("A nonempty idempotency key is required")
        allowed, reason = eligibility(order)
        if not allowed and self.fault != Fault.POLICY_BYPASS:
            raise AccessDenied(reason)
        self.refund_attempts += 1
        if self.transport == "always_timeout" or (
            self.transport == "timeout_before" and self.refund_attempts == 1
        ):
            raise Unavailable("Refund tool timed out before processing")
        if self.fault != Fault.DUPLICATE_REFUND:
            existing_key = self.store.refund_by_key(key)
            if existing_key and existing_key["order_id"] != order["id"]:
                raise AccessDenied("Idempotency key belongs to another operation")
            existing = self.store.existing_refund(order["id"])
            if existing:
                return {"refund_id": existing["id"], "amount": existing["amount"], "reused": True}
        refund = self.store.add_refund(order, key)
        if self.transport == "timeout_after" and self.refund_attempts == 1:
            raise Unavailable("Response lost after refund was committed")
        return {"refund_id": refund["id"], "amount": refund["amount"], "reused": False}
