from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")

# Tests may override this.
_frozen: datetime | None = None


def now() -> datetime:
    if _frozen is not None:
        return _frozen
    return datetime.now(TZ)


def set_frozen(dt: datetime | None) -> None:
    global _frozen
    if dt is None:
        _frozen = None
        return
    if dt.tzinfo is None:
        _frozen = dt.replace(tzinfo=TZ)
    else:
        _frozen = dt.astimezone(TZ)


def as_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)
