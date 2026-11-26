from typing import TypedDict
from .db import QueryResult

class AgentState(TypedDict, total=False):
    question: str
    schema: str
    queries: list[str]
    results: list[QueryResult]
    errors: list[str]
    repair_count: int
    last_error: str
    route: str
    answer: str
    chart: dict | None
    trace: list[dict]
