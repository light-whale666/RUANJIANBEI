"""Supervisor decision framework: paths, uncertainty, guards, and no invention."""

from app.agents.decision.guards import apply_guards
from app.agents.decision.llm import LlmDecisionModel
from app.agents.decision.rules import RuleDecisionModel
from app.agents.decision.types import Decision, DecisionContext, DecisionStep
from tests.conftest import auth_header


def _ask(client, username, text):
    res = client.post("/api/v1/ask", json={"text": text}, headers=auth_header(client, username))
    assert res.status_code == 200, res.text
    return res.json()


def _leaves(client, username):
    res = client.get("/api/v1/leaves", headers=auth_header(client, username))
    assert res.status_code == 200, res.text
    return res.json().get("items") or res.json() if isinstance(res.json(), list) else res.json().get("items", [])


def test_decision_paths_are_identifiable(client):
    knowledge = _ask(client, "stu.chen", "短假由谁审批？跨天病假需要什么材料？")
    assert knowledge["intent"] == "knowledge"
    dec = knowledge["decision"]
    assert dec["path"] == "knowledge.retrieve"
    assert dec["source"] == "rules"
    assert dec["uncertain"] is False
    assert "leave" in dec["knowledge_scope"]
    assert dec["steps"] and all("reason" in s and "action" in s for s in dec["steps"])
    assert any(s["id"].startswith("score.") or s["action"] == "score_intent" for s in dec["steps"])

    leave = _ask(client, "stu.chen", "明天上午去医院看病，帮我请个假")
    assert leave["intent"] == "leave"
    dec = leave["decision"]
    assert dec["path"] == "leave.draft_and_confirm"
    assert dec["source"] == "rules"
    assert dec["why_confirm"]
    assert dec["awaiting"] == "student_confirm"
    assert dec["steps"]

    aid = _ask(client, "stu.lin", "国家励志奖学金我能申请吗")
    assert aid["intent"] == "aid"
    dec = aid["decision"]
    assert dec["path"] == "aid.preview"
    assert dec["why_confirm"]
    assert dec["awaiting"] == "student_confirm"

    registration = _ask(client, "stu.chen", "新生报到当天几点前到宿舍办理入住？")
    assert registration["intent"] == "registration"
    dec = registration["decision"]
    assert dec["path"] in {"registration.retrieve", "knowledge.retrieve"}
    assert "enrollment" in dec["knowledge_scope"]
    assert dec["steps"]


def test_uncertain_question_does_not_create_drafts(client):
    chen = auth_header(client, "stu.chen")
    before = client.get("/api/v1/leaves", headers=chen)
    assert before.status_code == 200, before.text
    payload = before.json()
    before_n = len(payload.get("items") or payload if isinstance(payload, list) else [])

    data = _ask(client, "stu.chen", "那个事情帮我处理一下")
    dec = data["decision"]
    assert dec["uncertain"] is True
    assert dec["path"] == "uncertain.clarify"
    assert dec["awaiting"] == "clarification"
    assert dec["steps"]
    assert "没有改动任何学生数据" in data["answer"]["conclusion"] or "不能判断" in data["answer"]["conclusion"]

    after = client.get("/api/v1/leaves", headers=chen).json()
    after_n = len(after.get("items") or after if isinstance(after, list) else [])
    assert after_n == before_n

    drafts = client.get("/api/v1/aids/drafts", headers=chen)
    assert drafts.status_code == 200
    assert drafts.json().get("items") == []


def test_leave_and_aid_require_student_confirm_and_do_not_submit(client):
    leave = _ask(client, "stu.chen", "明天上午去办事，请个事假")
    dec = leave["decision"]
    assert dec["why_confirm"]
    assert dec["awaiting"] == "student_confirm"
    action = leave["answer"]["action"]
    assert action and action["ref"]["leave_id"]
    leave_id = action["ref"]["leave_id"]
    detail = client.get(f"/api/v1/leaves/{leave_id}", headers=auth_header(client, "stu.chen"))
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] in {"draft", "pending_confirm"}
    assert detail.json()["status"] not in {"submitted", "approving", "approved"}

    aid = _ask(client, "stu.lin", "励志奖学金我符合吗，帮我看看")
    dec = aid["decision"]
    assert dec["why_confirm"]
    assert dec["awaiting"] == "student_confirm"
    # Preview only: no draft created automatically
    listed = client.get("/api/v1/aids/drafts", headers=auth_header(client, "stu.lin"))
    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_no_key_uses_rules_source(client):
    data = _ask(client, "stu.chen", "短假由谁审批？")
    assert data["decision"]["source"] == "rules"


def test_apply_guards_blocks_llm_skipping_confirmation():
    ctx = DecisionContext(text="明天请假", role="student", authorized_fields=set())
    proposal = Decision(
        path="leave.draft_and_confirm",
        intent="leave",
        confidence=0.91,
        uncertain=False,
        source="llm",
        steps=[DecisionStep(id="llm.propose", action="llm_propose", reason="模型想直接提交请假", evidence=[])],
        why_confirm=None,
        awaiting=None,  # the model tried to skip confirmation
        knowledge_scope=["leave"],
        allow_mutation=True,
        should_prefill=True,
    )
    guarded = apply_guards(proposal, ctx)
    assert guarded.awaiting == "student_confirm"
    assert guarded.why_confirm
    assert any(s.id == "guard.student_confirm" for s in guarded.steps)


def test_apply_guards_blocks_mutation_when_uncertain():
    ctx = DecisionContext(text="帮我处理一下", role="student")
    proposal = Decision(
        path="leave.draft_and_confirm",
        intent="leave",
        confidence=0.3,
        uncertain=True,
        source="llm",
        steps=[],
        awaiting=None,
        allow_mutation=True,
        should_prefill=True,
    )
    guarded = apply_guards(proposal, ctx)
    assert guarded.path == "uncertain.clarify"
    assert guarded.allow_mutation is False
    assert guarded.awaiting == "clarification"
    assert any(s.action == "block_mutation" for s in guarded.steps)


def test_llm_stub_and_fallback():
    def fake_ok(_prompt, _system):
        return """{
          "intent": "aid",
          "confidence": 0.88,
          "uncertain": false,
          "path": "aid.preview",
          "knowledge_scope": ["aid"],
          "should_prefill": true,
          "awaiting": "student_confirm",
          "why_confirm": "应等学生确认",
          "reason": "问句在做奖助预审"
        }"""

    ctx = DecisionContext(text="励志奖学金我能申请吗", role="student", authorized_fields={"grades", "hardship"})
    decision = apply_guards(LlmDecisionModel(caller=fake_ok).decide(ctx), ctx)
    assert decision.source == "llm"
    assert decision.intent == "aid"
    assert decision.path == "aid.preview"
    assert decision.awaiting == "student_confirm"
    assert any(s.id == "llm.propose" for s in decision.steps)

    def fake_bad(_prompt, _system):
        raise RuntimeError("boom")

    decision = apply_guards(LlmDecisionModel(caller=fake_bad).decide(ctx), ctx)
    assert decision.source == "rules"
    assert any(s.action == "fallback_to_rules" for s in decision.steps)
    # Still a usable aid/knowledge decision, not a crash.
    assert decision.intent in {"aid", "knowledge"}
    assert decision.path in {"aid.preview", "knowledge.retrieve", "uncertain.clarify"}


def test_rule_model_scores_instead_of_bare_keyword():
    # A rule question containing 请假 should be knowledge, not a leave draft.
    ctx = DecisionContext(text="短假由谁审批？跨天病假需要什么材料？", role="student")
    raw = RuleDecisionModel().decide(ctx)
    guarded = apply_guards(raw, ctx)
    assert guarded.intent == "knowledge"
    assert guarded.path == "knowledge.retrieve"
    assert guarded.allow_mutation is False
    assert any(s.action == "score_intent" for s in guarded.steps)

    ctx2 = DecisionContext(text="明天上午去医院看病，帮我请个假", role="student")
    guarded2 = apply_guards(RuleDecisionModel().decide(ctx2), ctx2)
    assert guarded2.intent == "leave"
    assert guarded2.path == "leave.draft_and_confirm"
