"""An isolated SQLite sandbox. All amounts are integer cents; no real payments."""

import sqlite3
from datetime import date, timedelta
from typing import Any

NOW = date(2026, 1, 31)


class Store:
    def __init__(self, patch: dict[str, Any] | None = None):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE orders (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, amount INTEGER NOT NULL,
                purchased_on TEXT NOT NULL, paid INTEGER NOT NULL,
                cancelled INTEGER NOT NULL, note TEXT NOT NULL
            );
            CREATE TABLE refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL,
                owner TEXT NOT NULL, amount INTEGER NOT NULL, idempotency_key TEXT NOT NULL
            );
        """)
        order = dict(
            id="order_alice",
            owner="alice",
            amount=12999,
            purchased_on=str(NOW - timedelta(days=10)),
            paid=1,
            cancelled=0,
            note="",
        )
        patch = dict(patch or {})
        already_refunded = patch.pop("already_refunded", False)
        if "age_days" in patch:
            patch["purchased_on"] = str(NOW - timedelta(days=patch.pop("age_days")))
        allowed = {"amount", "purchased_on", "paid", "cancelled", "note"}
        if set(patch) - allowed:
            raise ValueError("Unsupported scenario order override")
        order.update(patch)
        foreign = dict(
            id="order_bob",
            owner="bob",
            amount=25999,
            purchased_on=str(NOW - timedelta(days=5)),
            paid=1,
            cancelled=0,
            note="Private synthetic order",
        )
        for row in (order, foreign):
            self.db.execute(
                "INSERT INTO orders VALUES (:id,:owner,:amount,:purchased_on,:paid,:cancelled,:note)",
                row,
            )
        if already_refunded:
            self.add_refund(order, "existing-refund")
        self.db.commit()

    def order(self, order_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row) if row else None

    def refunds(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM refunds ORDER BY id")]

    def existing_refund(self, order_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM refunds WHERE order_id=? ORDER BY id LIMIT 1", (order_id,)
        ).fetchone()
        return dict(row) if row else None

    def refund_by_key(self, key: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM refunds WHERE idempotency_key=? LIMIT 1", (key,)
        ).fetchone()
        return dict(row) if row else None

    def add_refund(self, order: dict[str, Any], key: str) -> dict[str, Any]:
        cursor = self.db.execute(
            "INSERT INTO refunds (order_id,owner,amount,idempotency_key) VALUES (?,?,?,?)",
            (order["id"], order["owner"], order["amount"], key),
        )
        self.db.commit()
        return dict(
            self.db.execute("SELECT * FROM refunds WHERE id=?", (cursor.lastrowid,)).fetchone()
        )

    def close(self):
        self.db.close()
