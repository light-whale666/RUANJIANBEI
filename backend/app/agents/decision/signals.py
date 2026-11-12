"""Extract observable signals used by the rule decision model to score intents."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.decision.types import DecisionContext
from app.services.dates import parse_leave_span

LEAVE_TERMS = ("请假", "销假", "假条", "病假", "事假", "请假条", "短假", "跨天假")
LEAVE_ACTIONS = ("帮我请", "我要请假", "请个假", "提交请假", "办理请假", "去请假", "申请请假", "帮我请假")
LEAVE_SITUATION = ("去医院", "看病", "回家", "有事", "明天", "今天", "后天", "上午", "下午")
LEAVE_RULE_QUESTIONS = ("谁审批", "由谁审批", "需要什么材料", "要什么材料", "怎么销假", "如何销假", "短假是")

AID_TERMS = ("奖学金", "助学金", "奖助", "励志", "困难认定")
AID_ACTIONS = ("我能申请", "能不能申请", "可以申请吗", "能否申请", "帮我申请", "我符合", "符合吗", "预审", "生成草稿")

REG_TERMS = ("报到", "入学", "入住", "入学须知", "宿舍办理")
REG_ACTIONS = ("我要报到", "去报到", "报到任务", "确认床位", "填写档案", "还有哪些报到")
REG_QUESTIONS = ("几点", "须知", "怎么报到", "如何办理入住", "何时入住")

CERT_TERMS = ("学生证", "补办", "开具证明")
# bare “证明” is weak on its own
CERT_STRONG = ("学生证", "补办学生证", "开具证明", "在读证明", "学籍证明")

VOL_TERMS = ("志愿者", "志愿活动", "志愿服务", "招募")
HW_TERMS = ("作业", "交作业", "提交作业")

QUESTION_MARKERS = ("怎么", "如何", "几点", "谁", "是否", "什么", "哪些", "吗", "规定", "须知", "能不能", "可否", "能否")
AMBIGUOUS_ONLY = ("那个", "那个事情", "帮我处理", "怎么办啊", "在吗", "你好", "问一下", "我想问个事", "有个事情")


def _hits(text: str, terms: tuple[str, ...]) -> list[str]:
    return [t for t in terms if t in text]


def _attachment_types(attachments: list) -> list[str]:
    types = []
    for item in attachments or []:
        if isinstance(item, str):
            types.append(item)
            continue
        if not isinstance(item, dict):
            continue
        for key in ("type", "kind", "content_type", "filename", "name"):
            val = item.get(key)
            if val:
                types.append(str(val))
    return types


@dataclass
class Signals:
    text: str
    leave_terms: list[str] = field(default_factory=list)
    leave_actions: list[str] = field(default_factory=list)
    leave_situation: list[str] = field(default_factory=list)
    leave_rule_questions: list[str] = field(default_factory=list)
    aid_terms: list[str] = field(default_factory=list)
    aid_actions: list[str] = field(default_factory=list)
    reg_terms: list[str] = field(default_factory=list)
    reg_actions: list[str] = field(default_factory=list)
    reg_questions: list[str] = field(default_factory=list)
    cert_terms: list[str] = field(default_factory=list)
    vol_terms: list[str] = field(default_factory=list)
    hw_terms: list[str] = field(default_factory=list)
    question_markers: list[str] = field(default_factory=list)
    attachment_types: list[str] = field(default_factory=list)
    medical_attachment: bool = False
    slots: dict = field(default_factory=dict)
    has_leave_span: bool = False
    looks_ambiguous: bool = False
    role: str = "student"
    is_freshman: bool = False
    has_leave_draft: bool = False
    has_aid_draft: bool = False
    available_knowledge: list[str] = field(default_factory=list)
    authorized_fields: list[str] = field(default_factory=list)

    def domain_hits(self, intent: str) -> list[str]:
        return {
            "leave": self.leave_terms + self.leave_actions + self.leave_situation,
            "aid": self.aid_terms + self.aid_actions,
            "registration": self.reg_terms + self.reg_actions + self.reg_questions,
            "certificate": self.cert_terms,
            "volunteer": self.vol_terms,
            "homework": self.hw_terms,
        }.get(intent, [])


def extract_signals(ctx: DecisionContext) -> Signals:
    text = ctx.text or ""
    slots = dict(ctx.parsed_slots or {})
    if not slots:
        try:
            slots = {k: v for k, v in (parse_leave_span(text) or {}).items() if v}
        except Exception:  # noqa: BLE001
            slots = {}
    atts = _attachment_types(ctx.attachments)
    medical = any(
        any(k in (t or "").lower() for k in ("medical", "病例", "诊断", "假条", "病假", "jpg", "png", "jpeg", "image"))
        for t in atts
    )
    # very short / vague utterances
    stripped = text.strip()
    ambiguous = (
        len(stripped) <= 1
        or stripped in {"你好", "在吗", "请问", "有人吗", "帮我看看", "那个"}
        or (any(p in stripped for p in AMBIGUOUS_ONLY) and not any(
            k in stripped for k in LEAVE_TERMS + AID_TERMS + REG_TERMS + CERT_STRONG + VOL_TERMS + HW_TERMS
        ))
    )
    return Signals(
        text=text,
        leave_terms=_hits(text, LEAVE_TERMS),
        leave_actions=_hits(text, LEAVE_ACTIONS),
        leave_situation=_hits(text, LEAVE_SITUATION),
        leave_rule_questions=_hits(text, LEAVE_RULE_QUESTIONS),
        aid_terms=_hits(text, AID_TERMS),
        aid_actions=_hits(text, AID_ACTIONS),
        reg_terms=_hits(text, REG_TERMS),
        reg_actions=_hits(text, REG_ACTIONS),
        reg_questions=_hits(text, REG_QUESTIONS),
        cert_terms=_hits(text, CERT_STRONG) or (_hits(text, CERT_TERMS) if "证明" in text and ("开具" in text or "补办" in text or "学生证" in text) else []),
        vol_terms=_hits(text, VOL_TERMS),
        hw_terms=_hits(text, HW_TERMS),
        question_markers=_hits(text, QUESTION_MARKERS),
        attachment_types=atts,
        medical_attachment=medical,
        slots=slots,
        has_leave_span=bool(slots.get("start_at") or slots.get("end_at")),
        looks_ambiguous=ambiguous,
        role=ctx.role,
        is_freshman=bool(ctx.is_freshman),
        has_leave_draft=bool(ctx.has_leave_draft),
        has_aid_draft=bool(ctx.has_aid_draft),
        available_knowledge=list(ctx.available_knowledge or []),
        authorized_fields=sorted(ctx.authorized_fields or []),
    )
