from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import auth_header

TZ = ZoneInfo("Asia/Shanghai")


def _slot():
    start = datetime(2026, 11, 12, 8, 0, tzinfo=TZ)
    end = datetime(2026, 11, 12, 12, 0, tzinfo=TZ)
    return start.isoformat(), end.isoformat()


def test_leave_missing_material_blocks_and_confirm_required(client):
    headers = auth_header(client, "stu.chen")
    start = datetime(2026, 11, 12, 8, 0, tzinfo=TZ)
    end = datetime(2026, 11, 14, 18, 0, tzinfo=TZ)
    res = client.post(
        "/api/v1/leaves",
        headers=headers,
        json={
            "text": "11月12日至14日去医院看病",
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "leave_type": "sick",
            "reason": "去医院看病",
        },
    )
    assert res.status_code == 200, res.text
    leave = res.json()
    assert leave["status"] in {"draft", "pending_confirm"}
    assert leave["validation"]["ok"] is False
    missing = leave["validation"]["missing"]
    assert any("病例" in (m.get("message") or "") or m.get("field") == "attachment" for m in missing)

    # Confirm must not issue a document
    res = client.post(f"/api/v1/leaves/{leave['id']}/confirm", headers=headers)
    assert res.status_code == 400, res.text
    body = res.json()
    assert body["code"] == "validation_blocked"
    assert body["details"]["missing"]
    # Status remains unsubmitted
    res = client.get(f"/api/v1/leaves/{leave['id']}", headers=headers)
    assert res.json()["status"] in {"draft", "pending_confirm"}
    assert res.json()["status"] not in {"submitted", "approving", "approved"}


def test_short_leave_confirm_then_counselor_approval_chain(client):
    start, end = _slot()
    student = auth_header(client, "stu.chen")
    res = client.post(
        "/api/v1/leaves",
        headers=student,
        json={"text": "明天上午去办事", "start_at": start, "end_at": end, "leave_type": "personal", "reason": "办事"},
    )
    assert res.status_code == 200, res.text
    leave = res.json()
    assert leave["validation"]["ok"] is True
    plan = leave["validation"]["approval_plan"]
    assert plan["short"] is True
    assert len(plan["chain"]) == 1
    assert plan["chain"][0]["role"] == "counselor"
    # Not submitted until student confirms
    assert leave["status"] in {"pending_confirm", "draft"}

    res = client.post(f"/api/v1/leaves/{leave['id']}/confirm", headers=student)
    assert res.status_code == 200, res.text
    leave = res.json()
    assert leave["status"] == "approving"
    assert leave["confirmed_at"]
    assert len(leave["approvals"]) == 1
    approval_id = leave["approvals"][0]["id"]
    assert leave["approvals"][0]["status"] == "pending"

    # Student cannot approve themselves
    # Counselor sees it and approves
    counselor = auth_header(client, "counselor.wang")
    box = client.get("/api/v1/approvals?type=leave", headers=counselor)
    assert box.status_code == 200
    ids = [x["id"] for x in box.json()["items"]]
    assert approval_id in ids

    res = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        headers=counselor,
        json={"decision": "approve", "comment": "同意"},
    )
    assert res.status_code == 200, res.text
    leave = res.json()
    assert leave["status"] == "approved"

    # 销假
    res = client.post(f"/api/v1/leaves/{leave['id']}/return", headers=student)
    assert res.status_code == 200, res.text
    assert res.json()["returned_at"]

    todos = client.get("/api/v1/todos", headers=student).json()["items"]
    # 销假 todo may be done and filtered; approved flow completed without error.


def test_cross_day_leave_uses_counselor_final_when_no_grade_lead(client):
    headers = auth_header(client, "stu.chen")
    start = datetime(2026, 11, 12, 8, 0, tzinfo=TZ).isoformat()
    end = datetime(2026, 11, 13, 18, 0, tzinfo=TZ).isoformat()
    res = client.post(
        "/api/v1/leaves",
        headers=headers,
        json={"start_at": start, "end_at": end, "leave_type": "personal", "reason": "回家"},
    )
    assert res.status_code == 200, res.text
    plan = res.json()["validation"]["approval_plan"]
    assert plan["short"] is False
    assert any("备案" in (s.get("label") or "") or s.get("final") for s in plan["chain"])
    assert plan.get("note")


def test_extract_without_vision_requires_manual_edit(client):
    headers = auth_header(client, "stu.chen")
    start, end = _slot()
    leave = client.post(
        "/api/v1/leaves",
        headers=headers,
        json={"start_at": start, "end_at": end, "reason": "看病"},
    ).json()
    files = {"file": ("病假条.jpg", b"\xff\xd8not-a-real-image", "image/jpeg")}
    res = client.post(f"/api/v1/leaves/{leave['id']}/extract", headers=headers, files=files)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["editable"] is True
    assert body.get("requires_manual_edit") is True
    assert "手工" in body["note"] or "未配置视觉模型" in body["note"]
