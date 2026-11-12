"""Rule-based Chinese date / leave-phrase extractor. No model required."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.services.clock import TZ, as_tz, now

WEEKDAYS = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6, "周天": 6,
            "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3, "星期五": 4, "星期六": 5, "星期日": 6}


def _at(base: datetime, hour: int, minute: int = 0) -> datetime:
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _next_weekday(base: datetime, weekday: int) -> datetime:
    delta = (weekday - base.weekday()) % 7
    if delta == 0:
        # "周三" spoken today after the period still means today if same day morning request;
        # if already past, keep today (student can edit).
        delta = 0
    return base + timedelta(days=delta)


def _period_hours(text: str) -> tuple[int, int]:
    if "上午" in text or "早上" in text or "早晨" in text:
        return 8, 12
    if "中午" in text:
        return 12, 14
    if "下午" in text:
        return 14, 18
    if "晚上" in text or "傍晚" in text:
        return 18, 21
    if "全天" in text or "一整天" in text:
        return 8, 18
    return 8, 18


def _parse_one_day(text: str, base: datetime) -> datetime | None:
    if "今天" in text or "今日" in text:
        return base
    if "明天" in text or "明日" in text:
        return base + timedelta(days=1)
    if "后天" in text:
        return base + timedelta(days=2)
    for label, wd in WEEKDAYS.items():
        if label in text:
            return _next_weekday(base, wd)
    m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = base.year
        try:
            dt = datetime(year, month, day, tzinfo=TZ)
        except ValueError:
            return None
        if dt < _at(base, 0) - timedelta(days=30):
            dt = datetime(year + 1, month, day, tzinfo=TZ)
        return dt
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=TZ)
    return None


def parse_leave_span(text: str, base: datetime | None = None) -> dict:
    base = as_tz(base or now())
    start_h, end_h = _period_hours(text)
    # Range: 周三至周五 / 11月12日至14日 / 明天到后天
    range_sep = re.search(
        r"(.+?)(?:至|到|—|~|-|至到)(.+)",
        text,
    )
    start_text, end_text = text, text
    if range_sep and not re.match(r"^\d{4}-", text):
        left, right = range_sep.group(1), range_sep.group(2)
        if _parse_one_day(left, base) or any(k in left for k in list(WEEKDAYS) + ["今天", "明天", "后天"]):
            start_text, end_text = left, right
            # "11月12日至14日" — right may be just a day number
            if re.match(r"^\s*\d{1,2}日", right) and "月" in left:
                month = re.search(r"(\d{1,2})月", left)
                if month:
                    end_text = f"{month.group(1)}月{right}"

    start_day = _parse_one_day(start_text, base)
    end_day = _parse_one_day(end_text, base)
    result: dict = {"reason": None, "destination": None, "leave_type": "personal"}
    if "医院" in text or "看病" in text or "发烧" in text or "病" in text or "就诊" in text or "病例" in text:
        result["leave_type"] = "sick"
        result["reason"] = result["reason"] or "就医/病假"
        if "医院" in text:
            result["destination"] = "医院"
    if "事假" in text:
        result["leave_type"] = "personal"
    if start_day is None:
        return result
    if end_day is None:
        end_day = start_day
    start_at = _at(start_day, start_h)
    end_at = _at(end_day, end_h)
    if end_at <= start_at:
        end_at = start_at + timedelta(hours=4)
    result["start_at"] = start_at
    result["end_at"] = end_at
    # Loose reason
    reason = re.sub(r"(今天|明天|后天|周[一二三四五六日天]|星期[一二三四五六日]|上午|下午|晚上|\d+月\d+日|至|到)", "", text)
    reason = reason.strip(" ，,。．")
    if reason:
        result["reason"] = reason
    return result


def duration_days(start: datetime, end: datetime) -> tuple[float, bool]:
    start, end = as_tz(start), as_tz(end)
    cross = start.date() != end.date()
    delta = end - start
    days = max(delta.total_seconds() / 86400.0, 1 / 24)
    # Natural-day count: inclusive calendar days when cross-day, else 1 if same day
    if not cross:
        natural = 1.0 if delta.total_seconds() > 0 else 0.0
    else:
        natural = (end.date() - start.date()).days + 1
    return natural, cross
