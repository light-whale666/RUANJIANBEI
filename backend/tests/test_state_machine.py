import pytest

from app.agents.workflow import (
    LEAVE_TRANSITIONS,
    StateError,
    after_all_approved,
    after_reject,
    can_withdraw_leave,
    transition,
)


def test_allowed_and_forbidden_leave_transitions():
    assert transition("draft", "pending_confirm") == "pending_confirm"
    assert transition("pending_confirm", "submitted") == "submitted"
    assert transition("submitted", "approving") == "approving"
    assert transition("approving", "approved") == "approved"
    assert transition("approving", "rejected") == "rejected"
    assert transition("approved", "pending_return") == "pending_return"
    with pytest.raises(StateError):
        transition("draft", "approved")
    with pytest.raises(StateError):
        transition("withdrawn", "submitted")
    with pytest.raises(StateError):
        transition("approved", "draft")
    # Cannot skip confirmation
    with pytest.raises(StateError):
        transition("draft", "submitted")


def test_withdraw_only_before_decisions():
    assert can_withdraw_leave("draft", False)
    assert can_withdraw_leave("pending_confirm", False)
    assert can_withdraw_leave("submitted", False)
    assert can_withdraw_leave("approving", False)
    assert can_withdraw_leave("approving", True) is False
    assert can_withdraw_leave("approved", False) is False
    assert can_withdraw_leave("rejected", False) is False


def test_approval_aggregation():
    assert after_all_approved(["approved"])
    assert after_all_approved(["approved", "approved"])
    assert after_all_approved(["approved", "pending"]) is False
    assert after_reject(["approved", "rejected"])
    assert after_reject(["pending", "approved"]) is False


def test_all_declared_states_have_a_row():
    expected = {
        "draft",
        "pending_confirm",
        "submitted",
        "approving",
        "approved",
        "pending_return",
        "rejected",
        "withdrawn",
        "expired",
    }
    assert set(LEAVE_TRANSITIONS) == expected
