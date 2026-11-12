"""Rule-based DecisionModel: score candidate intents from signals, with reasons.

This is not a single if-else keyword router. Signals are extracted first, each
candidate intent is scored independently, and a close top-two or a low top
score is marked uncertain.
"""

from __future__ import annotations

from app.agents.decision.signals import Signals, extract_signals
from app.agents.decision.types import Decision, DecisionContext, DecisionStep

# Below this, an operational intent is not trusted on its own.
OPERATIONAL_MIN = 0.45
# If the leading two scores are at least this close, treat as uncertain
# unless a dedicated tie-break applies (rule-question vs. action).
MARGIN = 0.12
# Knowledge is allowed at a lower raw score because "look it up" is the default
# for a well-formed question that matches no operational intent.
KNOWLEDGE_MIN = 0.28


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def _score_leave(sig: Signals) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    evidence: list[str] = []
    score = 0.0
    if sig.leave_terms:
        score += min(0.55, 0.28 * len(sig.leave_terms))
        reasons.append("命中请假相关词项")
        evidence.extend(sig.leave_terms)
    if sig.leave_actions:
        score += 0.30
        reasons.append("出现办理/申请类措辞，更像要请假而不是查规定")
        evidence.extend(sig.leave_actions)
    if sig.has_leave_span:
        score += 0.22
        reasons.append("已解析出请假起止时间槽位")
        evidence.append("start_at/end_at")
    elif sig.leave_situation:
        score += 0.14
        reasons.append("出现具体事由或时间线索")
        evidence.extend(sig.leave_situation)
    if sig.medical_attachment:
        score += 0.12
        reasons.append("附件类型提示病假材料")
        evidence.extend(sig.attachment_types)
    if sig.has_leave_draft:
        score += 0.08
        reasons.append("已有请假草稿，可能是在继续办理")
    # Asking about the rule, not requesting a leave.
    if (sig.leave_rule_questions or (sig.question_markers and not sig.leave_actions and not sig.has_leave_span and not sig.leave_situation)):
        if sig.leave_terms and not sig.leave_actions and not sig.has_leave_span:
            score *= 0.42
            reasons.append("问句在询问审批/材料等规定，削弱“去办理请假”得分")
            evidence.extend(sig.leave_rule_questions or sig.question_markers)
    return _clip(score), reasons, evidence


def _score_aid(sig: Signals) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    evidence: list[str] = []
    score = 0.0
    if sig.aid_terms:
        score += min(0.55, 0.30 * len(sig.aid_terms))
        reasons.append("命中奖助相关词项")
        evidence.extend(sig.aid_terms)
    if sig.aid_actions:
        score += 0.32
        reasons.append("在询问或请求奖助资格预审/申请")
        evidence.extend(sig.aid_actions)
    if sig.has_aid_draft:
        score += 0.08
        reasons.append("已有奖助草稿")
    # Pure "办法是怎么规定的" without 我能申请 / 符合吗 → dampen toward knowledge
    if sig.aid_terms and sig.question_markers and not sig.aid_actions and any(k in sig.text for k in ("规定", "办法", "条款", "如何规定")):
        score *= 0.45
        reasons.append("更像在查阅奖助办法，削弱“预审办理”得分")
    return _clip(score), reasons, evidence


def _score_registration(sig: Signals) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    evidence: list[str] = []
    score = 0.0
    if sig.reg_terms:
        score += min(0.50, 0.28 * len(sig.reg_terms))
        reasons.append("命中报到/入学相关词项")
        evidence.extend(sig.reg_terms)
    if sig.reg_actions:
        score += 0.30
        reasons.append("在查看或办理报到任务")
        evidence.extend(sig.reg_actions)
    if sig.reg_questions:
        score += 0.18
        reasons.append("在询问报到时间或须知")
        evidence.extend(sig.reg_questions)
    if sig.is_freshman and sig.reg_terms:
        score += 0.06
        reasons.append("当前角色为新生，报到意图略增强")
    return _clip(score), reasons, evidence


def _score_certificate(sig: Signals) -> tuple[float, list[str], list[str]]:
    if not sig.cert_terms:
        return 0.0, [], []
    return _clip(min(0.85, 0.4 * len(sig.cert_terms) + (0.25 if any(k in sig.text for k in ("补办", "开具", "办理")) else 0))), \
        ["命中证明/补证相关词项"], list(sig.cert_terms)


def _score_volunteer(sig: Signals) -> tuple[float, list[str], list[str]]:
    if not sig.vol_terms:
        return 0.0, [], []
    return _clip(min(0.85, 0.4 * len(sig.vol_terms))), ["命中志愿者/招募相关词项"], list(sig.vol_terms)


def _score_homework(sig: Signals) -> tuple[float, list[str], list[str]]:
    if not sig.hw_terms:
        return 0.0, [], []
    return _clip(min(0.85, 0.45 * len(sig.hw_terms))), ["命中作业相关词项"], list(sig.hw_terms)


def _score_knowledge(sig: Signals, domain_scores: dict[str, float]) -> tuple[float, list[str], list[str]]:
    reasons: list[str] = []
    evidence: list[str] = []
    score = 0.0
    if sig.question_markers:
        score += min(0.40, 0.12 * len(sig.question_markers))
        reasons.append("问句特征明显，适合先检索知识")
        evidence.extend(sig.question_markers)
    # If a domain is being asked as a rule question (no action), knowledge should lead.
    rule_like = False
    if sig.leave_terms and not sig.leave_actions and not sig.has_leave_span and (sig.leave_rule_questions or sig.question_markers):
        score += 0.38
        rule_like = True
        reasons.append("请假词项出现在规定/审批类问句中，优先走知识检索")
    if sig.aid_terms and not sig.aid_actions and any(k in sig.text for k in ("规定", "办法", "条款")):
        score += 0.34
        rule_like = True
        reasons.append("奖助词项出现在查阅办法的问句中，优先走知识检索")
    if sig.reg_terms and (sig.reg_questions or sig.question_markers) and not sig.reg_actions:
        score += 0.34
        rule_like = True
        reasons.append("报到/入学问句在查询须知或时间，可走检索")
    # A well-formed question with no operational domain still goes to retrieval.
    if sig.question_markers and max(domain_scores.values(), default=0) < 0.35:
        score = max(score, 0.40)
        reasons.append("没有稳定的办事意图，默认先检索知识库，无依据不编造")
    # Specific statements (e.g. quoting a clause) also go to retrieval, not "uncertain".
    # Uncertainty is reserved for short or vague utterances, or close operational ties.
    if not sig.looks_ambiguous and len((sig.text or "").strip()) >= 8:
        score = max(score, 0.38)
        if "默认先检索" not in "；".join(reasons):
            reasons.append("问句足够具体，默认先检索知识库，无依据不编造")
    if sig.available_knowledge and (rule_like or sig.question_markers or len((sig.text or "").strip()) >= 8):
        score += 0.04
        evidence.append("knowledge:" + ",".join(sig.available_knowledge))
    if sig.looks_ambiguous and not sig.question_markers and not rule_like:
        score = min(score, 0.2)
    return _clip(score), reasons, evidence


def _knowledge_scope(sig: Signals, intent: str) -> list[str]:
    scope = []
    if intent in {"leave"} or sig.leave_terms:
        scope.append("leave")
    if intent in {"aid"} or sig.aid_terms:
        scope.append("aid")
    if intent in {"registration"} or sig.reg_terms:
        scope.append("enrollment")
    if intent in {"certificate"} or sig.cert_terms:
        scope.append("certificate")
    if intent in {"volunteer"} or sig.vol_terms:
        scope.append("volunteer")
    if intent in {"homework"} or sig.hw_terms:
        scope.append("homework")
    # Keep unique, prefer the winning intent first
    if intent in {"leave", "aid"} and intent in scope:
        scope = [intent] + [s for s in scope if s != intent]
    if intent == "registration":
        scope = ["enrollment"] + [s for s in scope if s != "enrollment"]
    return list(dict.fromkeys(scope))


def _path_for(intent: str, sig: Signals, uncertain: bool) -> str:
    if uncertain:
        return "uncertain.clarify"
    if intent == "leave":
        return "leave.draft_and_confirm"
    if intent == "aid":
        return "aid.preview"
    if intent == "registration":
        if sig.reg_actions and not (sig.reg_questions or (sig.question_markers and not sig.reg_actions)):
            return "registration.view_tasks"
        if sig.reg_questions or sig.question_markers:
            return "registration.retrieve"
        return "registration.view_tasks"
    if intent == "certificate":
        return "certificate.guide"
    if intent == "volunteer":
        return "volunteer.guide"
    if intent == "homework":
        return "homework.view"
    return "knowledge.retrieve"


class RuleDecisionModel:
    source = "rules"

    def decide(self, ctx: DecisionContext) -> Decision:
        sig = extract_signals(ctx)
        steps: list[DecisionStep] = [
            DecisionStep(
                id="extract_signals",
                action="extract_signals",
                reason="先抽取词项、槽位、角色、已有草稿、附件类型和可检索知识类别，再对候选意图评分。",
                evidence=[
                    *(f"term:{t}" for t in (sig.leave_terms + sig.aid_terms + sig.reg_terms + sig.cert_terms + sig.vol_terms + sig.hw_terms)[:8]),
                    *(f"slot:{k}" for k in sig.slots),
                    f"role:{sig.role}",
                    *(f"knowledge:{k}" for k in sig.available_knowledge),
                ],
            )
        ]

        scored: dict[str, tuple[float, list[str], list[str]]] = {
            "leave": _score_leave(sig),
            "aid": _score_aid(sig),
            "registration": _score_registration(sig),
            "certificate": _score_certificate(sig),
            "volunteer": _score_volunteer(sig),
            "homework": _score_homework(sig),
        }
        domain_only = {k: v[0] for k, v in scored.items()}
        scored["knowledge"] = _score_knowledge(sig, domain_only)

        for intent, (score, reasons, evidence) in scored.items():
            if score <= 0 and intent != "knowledge":
                continue
            steps.append(DecisionStep(
                id=f"score.{intent}",
                action="score_intent",
                reason=("；".join(reasons) if reasons else "无线索") + f"（得分 {score:.2f}）",
                evidence=evidence,
            ))

        ranking = sorted(((k, v[0]) for k, v in scored.items()), key=lambda x: x[1], reverse=True)
        top_intent, top_score = ranking[0]
        second_intent, second_score = ranking[1] if len(ranking) > 1 else ("", 0.0)

        uncertain = False
        clarify_reason = ""
        if sig.looks_ambiguous and top_score < 0.5:
            uncertain = True
            clarify_reason = "问句过短或缺少可判别的办事/知识线索，不能判断要走哪条路径。"
        elif top_intent != "knowledge" and top_score < OPERATIONAL_MIN:
            if scored["knowledge"][0] >= KNOWLEDGE_MIN:
                top_intent, top_score = "knowledge", scored["knowledge"][0]
            else:
                uncertain = True
                clarify_reason = f"最高分意图「{top_intent}」得分 {top_score:.2f}，低于办事路径阈值 {OPERATIONAL_MIN}，且知识路径也不够明确。"
        elif top_intent != "knowledge" and (top_score - second_score) < MARGIN and second_score >= 0.35:
            # Close race. If knowledge is the runner-up and the leader is a
            # domain being asked as a rule, prefer knowledge. Otherwise uncertain.
            if second_intent == "knowledge" and top_score - second_score < 0.08:
                # still close after knowledge scored — if operational action is weak, switch
                if top_intent == "leave" and not sig.leave_actions and not sig.has_leave_span:
                    top_intent, top_score = "knowledge", scored["knowledge"][0]
                elif top_intent == "aid" and not sig.aid_actions:
                    top_intent, top_score = "knowledge", scored["knowledge"][0]
                elif top_intent == "registration" and not sig.reg_actions:
                    # keep registration but it will use retrieve path
                    pass
                else:
                    uncertain = True
                    clarify_reason = f"「{top_intent}」({top_score:.2f}) 与「{second_intent}」({second_score:.2f}) 得分接近，不能擅自选择。"
            elif second_intent != "knowledge":
                uncertain = True
                clarify_reason = f"「{top_intent}」({top_score:.2f}) 与「{second_intent}」({second_score:.2f}) 得分接近，不能擅自选择。"

        if uncertain:
            steps.append(DecisionStep(
                id="decide.uncertain",
                action="mark_uncertain",
                reason=clarify_reason or "候选意图不够明确。",
                evidence=[f"{k}:{v[0]:.2f}" for k, v in scored.items() if v[0] > 0],
            ))
        else:
            steps.append(DecisionStep(
                id="decide.select",
                action="select_path",
                reason=f"采用得分最高且间隔足够的意图「{top_intent}」（{top_score:.2f}）。",
                evidence=[f"{k}:{v[0]:.2f}" for k, v in scored.items() if v[0] > 0],
            ))

        scope = _knowledge_scope(sig, top_intent if not uncertain else "knowledge")
        # For a pure knowledge win driven by a domain question, keep that domain scope.
        if top_intent == "knowledge":
            scope = _knowledge_scope(sig, "knowledge")

        path = _path_for(top_intent if not uncertain else "knowledge", sig, uncertain)
        intent = "knowledge" if uncertain and top_score < KNOWLEDGE_MIN else (top_intent if not uncertain else top_intent)

        should_prefill = path in {"leave.draft_and_confirm", "aid.preview", "aid.draft_and_confirm"}
        return Decision(
            path=path,
            intent=intent,
            confidence=round(float(top_score if not uncertain else min(top_score, 0.4)), 3),
            uncertain=uncertain,
            source="rules",
            steps=steps,
            why_confirm=None,
            awaiting="clarification" if uncertain else None,
            knowledge_scope=scope,
            allow_mutation=False,  # guards decide
            should_prefill=should_prefill and not uncertain,
            scores={k: round(v[0], 3) for k, v in scored.items()},
        )
