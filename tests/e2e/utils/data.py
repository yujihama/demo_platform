"""Faker-based utilities for E2E tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from faker import Faker

faker = Faker("ja_JP")


@dataclass
class InvoiceData:
    invoice_number: str
    vendor_name: str
    amount: float
    currency: str
    issue_date: str


def build_invoice_samples(count: int = 3) -> List[InvoiceData]:
    invoices: List[InvoiceData] = []
    for _ in range(count):
        invoices.append(
            InvoiceData(
                invoice_number=faker.bothify(text="INV-####-??"),
                vendor_name=faker.company(),
                amount=round(faker.pyfloat(min_value=50_000, max_value=1_500_000), 2),
                currency="JPY",
                issue_date=faker.date_this_year().isoformat(),
            )
        )
    return invoices

