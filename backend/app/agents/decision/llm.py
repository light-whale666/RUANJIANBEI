"""LLM DecisionModel: structured routing only. Never invents regulation text.

On missing key, transport error, or unparsable output, falls back to the
RuleDecisionModel and records the fallback in the decision steps.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from app.agents.decision.rules import RuleDecisionModel
from app.agents.decision.signals import extract_signals
from app.agents.decision.types import Decision, DecisionContext, DecisionStep, INTENTS
from app.config import get_settings

SYSTEM_PROMPT = """你是校园办事助手的总管智能体，只负责路由与决策，不撰写、不编造任何校规条款。
根据学生问句和已抽取信号，输出一个 JSON 对象，不要输出其它文字。字段如下：
{
  "intent": "knowledge|leave|aid|registration|certificate|volunteer|homework",
  "confidence": 0.0到1.0的数,
  "uncertain": true或false,
  "path": "leave.draft_and_confirm|aid.preview|knowledge.retrieve|registration.retrieve|registration.view_tasks|certificate.guide|volunteer.guide|homework.view|uncertain.clarify",
  "knowledge_scope": ["leave"|"aid"|"enrollment"|...],
  "should_prefill": true或false,
  "awaiting": "student_confirm"|"teacher_approval"|"clarification"|null,
  "why_confirm": 字符串或null,
  "reason": 一句话说明为什么走这条路径
}
规则：
- 拿不准时 uncertain=true，path=uncertain.clarify，不要建议改学生数据。
- 查规定、问审批人、问材料、问报到时间：走 knowledge.retrieve 或 registration.retrieve，不要预填或生成草稿。
- 学生明确要请假或已给出时间/事由：leave.draft_and_confirm，必须 awaiting=student_confirm。
- 问能否申请奖助或要预审：aid.preview，必须 awaiting=student_confirm，系统不得自动提交。
- 知识正文只能来自后续检索片段；你不得在 reason 里编造条款内容。
"""


def _parse_json_payload(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty llm output")
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if fence:
        raw = fence.group(1)
    else:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("llm output is not an object")
    return data


def default_llm_caller(prompt: str, system: str) -> str:
    """OpenAI-compatible chat completion. Isolated so tests can stub it."""
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not configured")
    import httpx

    base = (settings.llm_base_url or "https://api.deepseek.com").rstrip("/")
    url = base + ("/chat/completions" if not base.endswith("/chat/completions") else "")
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.llm_model or "deepseek-chat",
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    with httpx.Client(timeout=20.0) as client:
        res = client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        body = res.json()
    return body["choices"][0]["message"]["content"]


class LlmDecisionModel:
    source = "llm"

    def __init__(
        self,
        fallback: RuleDecisionModel | None = None,
        caller: Callable[[str, str], str] | None = None,
    ):
        self.fallback = fallback or RuleDecisionModel()
        self.caller = caller or default_llm_caller

    def decide(self, ctx: DecisionContext) -> Decision:
        settings = get_settings()
        if not settings.llm_api_key and self.caller is default_llm_caller:
            decision = self.fallback.decide(ctx)
            decision.add_step(
                "llm.unavailable",
                "fallback_to_rules",
                "未配置 LLM_API_KEY，使用可说明依据的规则决策兜底。",
                [],
            )
            return decision

        sig = extract_signals(ctx)
        user_payload = {
            "text": ctx.text,
            "role": ctx.role,
            "is_freshman": ctx.is_freshman,
            "signals": {
                "leave_terms": sig.leave_terms,
                "leave_actions": sig.leave_actions,
                "leave_slots": list(sig.slots),
                "aid_terms": sig.aid_terms,
                "aid_actions": sig.aid_actions,
                "registration_terms": sig.reg_terms,
                "question_markers": sig.question_markers,
                "attachment_types": sig.attachment_types,
                "available_knowledge": sig.available_knowledge,
                "authorized_fields": sig.authorized_fields,
                "has_leave_draft": sig.has_leave_draft,
                "has_aid_draft": sig.has_aid_draft,
            },
        }
        prompt = "请根据下列上下文输出决策 JSON：\n" + json.dumps(user_payload, ensure_ascii=False)
        try:
            raw = self.caller(prompt, SYSTEM_PROMPT)
            data = _parse_json_payload(raw)
        except Exception as exc:  # noqa: BLE001
            decision = self.fallback.decide(ctx)
            decision.add_step(
                "llm.failed",
                "fallback_to_rules",
                f"模型调用或解析失败，已回退规则决策。原因：{type(exc).__name__}",
                [],
            )
            return decision

        intent = data.get("intent") or "knowledge"
        if intent not in INTENTS:
            intent = "knowledge"
        uncertain = bool(data.get("uncertain"))
        confidence = data.get("confidence")
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        path = data.get("path") or ("uncertain.clarify" if uncertain else "knowledge.retrieve")
        scope = data.get("knowledge_scope") or []
        if isinstance(scope, str):
            scope = [scope]
        awaiting = data.get("awaiting")
        if awaiting not in {"student_confirm", "teacher_approval", "clarification", None}:
            awaiting = None
        why = data.get("why_confirm")
        if why == "":
            why = None
        reason = data.get("reason") or "模型给出了结构化路由结果。"
        should_prefill = bool(data.get("should_prefill"))
        if uncertain:
            path = "uncertain.clarify"
            should_prefill = False
        return Decision(
            path=str(path),
            intent=intent,
            confidence=confidence,
            uncertain=uncertain,
            source="llm",
            steps=[
                DecisionStep(
                    id="llm.propose",
                    action="llm_propose",
                    reason=str(reason),
                    evidence=[f"path:{path}", f"intent:{intent}"],
                )
            ],
            why_confirm=why,
            awaiting=awaiting,
            knowledge_scope=[str(s) for s in scope],
            allow_mutation=False,
            should_prefill=should_prefill,
        )


def build_decision_model(caller: Callable[[str, str], str] | None = None) -> RuleDecisionModel | LlmDecisionModel:
    settings = get_settings()
    if caller is not None:
        return LlmDecisionModel(fallback=RuleDecisionModel(), caller=caller)
    if settings.llm_api_key:
        return LlmDecisionModel(fallback=RuleDecisionModel())
    return RuleDecisionModel()
