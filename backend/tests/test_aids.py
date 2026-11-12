from tests.conftest import auth_header


def test_aid_only_pushes_when_qualified(client):
    lin = auth_header(client, "stu.lin")
    zhao = auth_header(client, "stu.zhao")

    lin_matches = client.get("/api/v1/aids/matches", headers=lin)
    assert lin_matches.status_code == 200, lin_matches.text
    items = lin_matches.json()["items"]
    assert items, "符合条件的学生应看到预审项目"
    assert all(i.get("auto_submit") is False for i in items)
    assert any("励志" in i["name"] for i in items)
    assert items[0]["reasons"]

    zhao_matches = client.get("/api/v1/aids/matches", headers=zhao)
    assert zhao_matches.status_code == 200
    assert zhao_matches.json()["items"] == []

    # Reminders: lin has eligibility, zhao must not
    lin_rem = client.get("/api/v1/reminders", headers=lin).json()["items"]
    assert any(r["category"] == "eligibility" for r in lin_rem)
    zhao_rem = client.get("/api/v1/reminders", headers=zhao).json()["items"]
    assert not any(r["category"] == "eligibility" for r in zhao_rem)

    # Muting eligibility hides reminders but keeps the todo
    res = client.post("/api/v1/reminders/categories/eligibility/mute", headers=lin)
    assert res.status_code == 200
    lin_rem2 = client.get("/api/v1/reminders", headers=lin).json()["items"]
    assert not any(r["category"] == "eligibility" for r in lin_rem2)
    todos = client.get("/api/v1/todos", headers=lin).json()["items"]
    assert any(t["type"] == "aid" for t in todos)


def test_aid_draft_requires_confirm_and_does_not_auto_submit(client):
    lin = auth_header(client, "stu.lin")
    matches = client.get("/api/v1/aids/matches", headers=lin).json()["items"]
    program_id = matches[0]["program_id"]
    res = client.post(f"/api/v1/aids/{program_id}/draft", headers=lin, json={"statement": "申请陈述"})
    assert res.status_code == 200, res.text
    draft = res.json()
    assert draft["status"] in {"draft", "pending_confirm"}
    assert draft["auto_submit"] is False

    res = client.post(f"/api/v1/aids/drafts/{draft['id']}/confirm", headers=lin)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "confirmed_pending_submit"
    assert body["auto_submit"] is False
    assert "自动提交" not in (body.get("note") or "") or "不会自动提交" in (body.get("note") or "")

    # Unqualified student cannot create a draft
    zhao = auth_header(client, "stu.zhao")
    res = client.post(f"/api/v1/aids/{program_id}/draft", headers=zhao, json={})
    assert res.status_code == 400
    assert res.json()["code"] == "validation_blocked"


def test_todos_include_homework_volunteer_and_enrollment(client):
    chen = auth_header(client, "stu.chen")
    lin = auth_header(client, "stu.lin")
    chen_todos = client.get("/api/v1/todos", headers=chen).json()["items"]
    assert any(t["type"] == "registration" and t.get("group") == "enrollment" for t in chen_todos)
    # Freshman should not be able to sign up for volunteer (year >= 2)
    vol = next(t for t in chen_todos if t["type"] == "volunteer")
    res = client.post(f"/api/v1/tasks/{vol['ref_id']}/submit", headers=chen, json={"available_slots": "周六"})
    assert res.status_code == 400
    assert res.json()["code"] == "validation_blocked"

    lin_todos = client.get("/api/v1/todos", headers=lin).json()["items"]
    assert any(t["type"] == "homework" for t in lin_todos)
    assert any(t["type"] == "volunteer" for t in lin_todos)
    vol = next(t for t in lin_todos if t["type"] == "volunteer")
    res = client.post(f"/api/v1/tasks/{vol['ref_id']}/submit", headers=lin, json={"available_slots": "周六上午", "confirm": True})
    assert res.status_code == 200, res.text


def test_my_applications_and_attachments_and_aid_drafts_list(client):
    lin = auth_header(client, "stu.lin")
    chen = auth_header(client, "stu.chen")
    # create a leave so chen has an application
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Shanghai")
    start = datetime(2026, 11, 12, 8, 0, tzinfo=tz).isoformat()
    end = datetime(2026, 11, 12, 12, 0, tzinfo=tz).isoformat()
    leave = client.post(
        "/api/v1/leaves",
        headers=chen,
        json={"start_at": start, "end_at": end, "reason": "办事", "leave_type": "personal"},
    )
    assert leave.status_code == 200, leave.text

    apps = client.get("/api/v1/me/applications", headers=chen)
    assert apps.status_code == 200, apps.text
    items = apps.json()["items"]
    assert any(i["kind"] == "leave" and i["status"] for i in items)

    files = client.get("/api/v1/me/attachments", headers=chen)
    assert files.status_code == 200
    assert "items" in files.json()

    # upload attachment
    res = client.post(
        "/api/v1/attachments",
        headers=chen,
        files={"file": ("假条.jpg", b"fake-bytes", "image/jpeg")},
        data={"kind": "medical"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"]
    assert body["filename"] == "假条.jpg"
    assert body.get("valid_until") or body.get("expires_at")

    files = client.get("/api/v1/me/attachments", headers=chen).json()["items"]
    assert any(f["filename"] == "假条.jpg" for f in files)

    # alias
    res = client.post(
        "/api/v1/uploads",
        headers=chen,
        files={"file": ("note.txt", b"ok", "text/plain")},
    )
    assert res.status_code == 200, res.text

    # aid drafts list exists (may be empty before creating)
    listed = client.get("/api/v1/aids/drafts", headers=lin)
    assert listed.status_code == 200, listed.text
    matches = client.get("/api/v1/aids/matches", headers=lin).json()["items"]
    program_id = matches[0]["program_id"]
    draft = client.post(f"/api/v1/aids/{program_id}/draft", headers=lin, json={"statement": "陈述"}).json()
    listed = client.get("/api/v1/aids/drafts", headers=lin).json()["items"]
    assert any(d["id"] == draft["id"] for d in listed)
    assert listed[0]["title"]
