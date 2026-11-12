"""Photo / text field extraction. Results are always editable and never treated as validated evidence."""

from app.config import get_settings
from app.services.dates import parse_leave_span


def extract_from_text(text: str, now=None) -> dict:
    parsed = parse_leave_span(text, now)
    return {
        "extracted": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in parsed.items() if v is not None},
        "editable": True,
        "note": "抽取结果可修改，不能直接作为已校验材料。",
    }


def extract_from_image(_content: bytes, filename: str | None = None) -> dict:
    settings = get_settings()
    if not settings.llm_api_key:
        return {
            "extracted": {},
            "editable": True,
            "note": "当前未配置视觉模型，请在表单中手工核对并修改时间、事由、材料类型。抽取结果不能直接作为已校验材料。",
            "requires_manual_edit": True,
        }
    # A configured key still must not auto-validate. We do not invent fields without a real call.
    return {
        "extracted": {},
        "editable": True,
        "note": "已配置模型但初版照片抽取需人工核对，请手工修改时间、事由、材料类型。抽取结果不能直接作为已校验材料。",
        "requires_manual_edit": True,
    }
