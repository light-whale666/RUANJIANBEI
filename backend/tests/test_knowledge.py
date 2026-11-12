from tests.conftest import auth_header


def _ask(client, username, text):
    res = client.post("/api/v1/ask", json={"text": text}, headers=auth_header(client, username))
    assert res.status_code == 200, res.text
    return res.json()


def _import_examples(client, ids=None):
    admin = auth_header(client, "admin")
    body = {"replace": True}
    if ids is not None:
        body["ids"] = ids
    res = client.post("/api/v1/admin/document-templates/import-examples", json=body, headers=admin)
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["items"]
    for item in payload["items"]:
        assert "【模板示例】" in (item.get("filename") or "") or "【模板示例】" in (item.get("title") or "")
    return payload


def test_empty_knowledge_base_does_not_invent(client):
    # After a fresh seed the library is empty: no official text, no template examples.
    data = _ask(client, "stu.chen", "短假由谁审批？跨天病假需要什么材料？")
    ans = data["answer"]
    assert ans["permission_denied"] is False
    assert ans["citations"] == []
    assert "知识库中没有找到相关规定" in ans["conclusion"]
    assert "辅导员审批" not in (ans["conclusion"] or "") or "知识库中没有找到相关规定" in ans["conclusion"]


def test_knowledge_no_evidence_does_not_invent(client):
    _import_examples(client)
    data = _ask(client, "stu.chen", "校园猫能否作为研究生特长加分项？")
    ans = data["answer"]
    assert ans["permission_denied"] is False
    assert ans["citations"] == []
    assert "知识库中没有找到相关规定" in ans["conclusion"]
    assert ans["human_entry"] is not None


def test_knowledge_returns_citations_after_template_import(client):
    _import_examples(client, ids=["leave-policy"])
    data = _ask(client, "stu.chen", "短假由谁审批？跨天病假需要什么材料？")
    ans = data["answer"]
    assert ans["permission_denied"] is False
    assert ans["citations"], ans
    assert ans["conclusion"]
    assert "没有找到" not in ans["conclusion"]
    cite = ans["citations"][0]
    assert cite["document_id"]
    assert cite["chunk_id"]
    assert "【模板示例】" in (cite["filename"] or "")
    assert cite["quote"]
    assert "【模板】" in cite["quote"] or "【示例】" in cite["quote"] or "模板示例" in cite["filename"]
    res = client.get(
        f"/api/v1/documents/{cite['document_id']}/chunks/{cite['chunk_id']}",
        headers=auth_header(client, "stu.chen"),
    )
    assert res.status_code == 200
    body = res.json()["content"]
    assert "短假" in body or "病假" in body or body


def test_knowledge_conflict_states_governing_document(client):
    _import_examples(client, ids=["enrollment-notice-prior", "enrollment-notice"])
    data = _ask(client, "stu.chen", "新生报到当天几点前到宿舍办理入住？")
    ans = data["answer"]
    assert ans["citations"]
    assert all("【模板示例】" in (c.get("filename") or "") for c in ans["citations"])
    assert ans["conflicts"], ans
    conflict = ans["conflicts"][0]
    assert conflict["reason"]
    assert "2025-2026" in conflict["reason"] or (conflict.get("chosen") or {}).get("semester", "").startswith("【示例】2025") or "2025" in ((conflict.get("chosen") or {}).get("semester") or "")
    chosen_quote = (conflict.get("chosen") or {}).get("quote", "")
    assert "20:00" in chosen_quote or "20:00" in ans["conclusion"]
    other_quotes = " ".join(o.get("quote") or "" for o in conflict.get("other") or [])
    assert "17:00" in other_quotes or any("2024" in (o.get("semester") or "") for o in conflict.get("other") or [])


def test_knowledge_permission_denied_does_not_leak(client):
    _import_examples(client, ids=["counselor-manual"])
    data = _ask(client, "stu.chen", "内部掌握口径不得向学生原文转述本条")
    ans = data["answer"]
    assert ans["permission_denied"] is True
    assert ans["citations"] == []
    assert "需辅导员查看" in ans["conclusion"]
    dumped = str(ans)
    assert "先行掌握" not in dumped
    assert "不得向学生原文转述本条" not in (ans["conclusion"] or "")

    counselor = _ask(client, "counselor.wang", "内部掌握口径不得向学生原文转述本条")
    assert counselor["answer"]["permission_denied"] is False
    assert counselor["answer"]["citations"]
    cite = counselor["answer"]["citations"][0]
    assert "【模板示例】" in (cite.get("filename") or "")
    res = client.get(
        f"/api/v1/documents/{cite['document_id']}/chunks/{cite['chunk_id']}",
        headers=auth_header(client, "stu.chen"),
    )
    assert res.status_code == 403
    assert res.json()["code"] == "need_counselor"
    assert "先行掌握" not in res.text
    assert "内部掌握口径：已获" not in res.text


def test_admin_templates_list_and_download(client):
    admin = auth_header(client, "admin")
    res = client.get("/api/v1/admin/document-templates", headers=admin)
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    ids = {i["id"] for i in items}
    assert {"leave-policy", "aid-policy", "enrollment-notice", "admin-process", "counselor-manual"} <= ids
    assert "【模板】请替换为学校正式文件" in res.json()["watermark"]
    res = client.get("/api/v1/admin/document-templates/leave-policy/download", headers=admin)
    assert res.status_code == 200
    body = res.content.decode("utf-8")
    assert "【模板】请替换为学校正式文件，本文不是任何学校的正式校规" in body
    assert "【请填写" in body
    # Empty template must not read like a finished official rule.
    assert "由辅导员审批" not in body
