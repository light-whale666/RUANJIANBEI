from tests.conftest import auth_header


def _ask(client, username, text):
    res = client.post("/api/v1/ask", json={"text": text}, headers=auth_header(client, username))
    assert res.status_code == 200, res.text
    return res.json()


def test_knowledge_returns_citations(client):
    data = _ask(client, "stu.chen", "短假由谁审批？跨天病假需要什么材料？")
    ans = data["answer"]
    assert ans["permission_denied"] is False
    assert ans["citations"], ans
    assert ans["conclusion"]
    assert "没有找到" not in ans["conclusion"]
    cite = ans["citations"][0]
    assert cite["document_id"]
    assert cite["chunk_id"]
    assert cite["filename"]
    assert cite["semester"]
    assert cite["quote"]
    # student can open the source chunk
    res = client.get(
        f"/api/v1/documents/{cite['document_id']}/chunks/{cite['chunk_id']}",
        headers=auth_header(client, "stu.chen"),
    )
    assert res.status_code == 200
    assert "短假" in res.json()["content"] or "病假" in res.json()["content"] or res.json()["content"]


def test_knowledge_no_evidence_does_not_invent(client):
    data = _ask(client, "stu.chen", "校园猫能否作为研究生特长加分项？")
    ans = data["answer"]
    assert ans["permission_denied"] is False
    assert ans["citations"] == []
    assert "知识库中没有找到相关规定" in ans["conclusion"]
    assert ans["human_entry"] is not None


def test_knowledge_conflict_states_governing_document(client):
    data = _ask(client, "stu.chen", "新生报到当天几点前到宿舍办理入住？")
    ans = data["answer"]
    assert ans["citations"]
    assert ans["conflicts"], ans
    conflict = ans["conflicts"][0]
    assert conflict["reason"]
    assert "2025-2026" in conflict["reason"] or (conflict.get("chosen") or {}).get("semester", "").startswith("2025")
    assert "20:00" in (conflict.get("chosen") or {}).get("quote", "") or "20:00" in ans["conclusion"]
    # The overruled older rule is still listed
    other_quotes = " ".join(o.get("quote") or "" for o in conflict.get("other") or [])
    assert "17:00" in other_quotes or any("2024" in (o.get("semester") or "") for o in conflict.get("other") or [])


def test_knowledge_permission_denied_does_not_leak(client):
    data = _ask(client, "stu.chen", "内部掌握口径不得向学生原文转述本条")
    ans = data["answer"]
    assert ans["permission_denied"] is True
    assert ans["citations"] == []
    assert "需辅导员查看" in ans["conclusion"]
    # body must not contain the internal clause
    dumped = str(ans)
    assert "先行掌握" not in dumped
    assert "不得向学生原文转述本条" not in (ans["conclusion"] or "")

    # Direct chunk access is 403 without leaking text
    # Find the internal document as admin/counselor then probe as student
    # Use counselor to list? no list for students. Query DB via asking as counselor.
    counselor = _ask(client, "counselor.wang", "内部掌握口径不得向学生原文转述本条")
    assert counselor["answer"]["permission_denied"] is False
    assert counselor["answer"]["citations"]
    cite = counselor["answer"]["citations"][0]
    res = client.get(
        f"/api/v1/documents/{cite['document_id']}/chunks/{cite['chunk_id']}",
        headers=auth_header(client, "stu.chen"),
    )
    assert res.status_code == 403
    assert res.json()["code"] == "need_counselor"
    assert "先行掌握" not in res.text
    assert "内部掌握口径：已获" not in res.text
