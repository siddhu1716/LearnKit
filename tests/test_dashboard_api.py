from Docs.server import _record_to_api
from learnkit.schemas.skill import SkillRecord


def test_record_to_api_marks_captured_procedure_as_procedural():
    record = SkillRecord(
        task_type="refund_support",
        domains={"customer_support": 0.95},
        content={
            "procedure": [
                {"tool": "find_customer", "args": {"email": "ada@example.com"}},
                {"tool": "issue_refund", "args": {"order_id": "ord_1001"}},
            ],
            "tool_sequence": ["find_customer", "issue_refund"],
        },
    )

    payload = _record_to_api(record)

    assert payload["is_procedural"] is True
    assert payload["step_count"] == 2
    assert payload["tool_sequence"] == ["find_customer", "issue_refund"]