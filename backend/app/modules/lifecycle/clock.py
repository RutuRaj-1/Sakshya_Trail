"""
Module 5 — Lifecycle Clock & Date-Boundary Semantics
Provides deterministic, timezone-aware calendar date calculations, injectable clocks
for testing, and demo date-advance mechanisms without calendar date shifts.
"""
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone, timedelta
from typing import Optional, Union
from zoneinfo import ZoneInfo

from app.core.config import settings


class Clock(ABC):
    """Abstract clock interface to guarantee testability and determinism."""

    @abstractmethod
    def now_utc(self) -> datetime:
        """Current instant in UTC."""
        pass

    @abstractmethod
    def today_in_tz(self, tz_name: Optional[str] = None) -> date:
        """Current calendar date at the date boundary of the specified timezone."""
        pass


class SystemClock(Clock):
    """Standard system clock using operating system time."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def today_in_tz(self, tz_name: Optional[str] = None) -> date:
        target_tz = ZoneInfo(tz_name or settings.LIFECYCLE_DEFAULT_TIMEZONE)
        return datetime.now(target_tz).date()


class SimulatedClock(Clock):
    """
    Clock for testing and authorized demo scenarios with controllable offset or fixed date.
    Strictly isolated from production.
    """

    def __init__(
        self,
        fixed_date: Optional[date] = None,
        fixed_dt: Optional[datetime] = None,
        offset_days: int = 0,
        default_tz: Optional[str] = None,
    ):
        self._default_tz = default_tz or settings.LIFECYCLE_DEFAULT_TIMEZONE
        if fixed_dt is not None:
            if fixed_dt.tzinfo is None:
                self._fixed_dt = fixed_dt.replace(tzinfo=timezone.utc)
            else:
                self._fixed_dt = fixed_dt.astimezone(timezone.utc)
        elif fixed_date is not None:
            # Construct noon UTC on given calendar date to avoid boundary clipping
            self._fixed_dt = datetime(
                fixed_date.year, fixed_date.month, fixed_date.day, 12, 0, 0, tzinfo=timezone.utc
            )
        else:
            self._fixed_dt = datetime.now(timezone.utc)

        self._offset = timedelta(days=offset_days)

    def advance_days(self, days: int) -> None:
        """Advance simulated clock by a specific number of days."""
        self._offset += timedelta(days=days)

    def set_date(self, target_date: date) -> None:
        """Set simulated clock explicitly to a calendar date."""
        self._fixed_dt = datetime(
            target_date.year, target_date.month, target_date.day, 12, 0, 0, tzinfo=timezone.utc
        )
        self._offset = timedelta(0)

    def now_utc(self) -> datetime:
        return self._fixed_dt + self._offset

    def today_in_tz(self, tz_name: Optional[str] = None) -> date:
        tz = ZoneInfo(tz_name or self._default_tz)
        current = self.now_utc().astimezone(tz)
        return current.date()


# Default singleton instance
system_clock = SystemClock()
_active_clock: Clock = system_clock


def get_current_clock() -> Clock:
    """Returns the current globally active clock instance."""
    return _active_clock


def set_current_clock(clock: Clock) -> None:
    """Sets the active clock (e.g. to a SimulatedClock in tests or demo mode)."""
    global _active_clock
    _active_clock = clock


def reset_to_system_clock() -> None:
    """Resets the active clock back to the real operating system clock."""
    global _active_clock
    _active_clock = system_clock


def get_clock_status(tz_name: Optional[str] = None) -> dict:
    """Introspects current clock mode and simulated offsets."""
    tz = tz_name or settings.LIFECYCLE_DEFAULT_TIMEZONE
    clock = get_current_clock()
    is_simulated = isinstance(clock, SimulatedClock)
    offset_days = clock._offset.days if is_simulated else 0

    return {
        "is_simulated": is_simulated,
        "active_timezone": tz,
        "today": clock.today_in_tz(tz).isoformat(),
        "now_utc": clock.now_utc().isoformat(),
        "offset_days": offset_days,
        "disclaimer": "DEMO DATE SIMULATION — NOT REAL TIME" if is_simulated else None,
    }


def get_calendar_days_between(start_date: Optional[date], end_date: Optional[date]) -> Optional[int]:
    """
    Computes exact integer calendar days between two dates: end_date - start_date.
    Returns None if either date is None or invalid, without raising arbitrary exceptions.
    """
    if start_date is None or end_date is None:
        return None
    try:
        return (end_date - start_date).days
    except Exception:
        return None


def calculate_due_date(base_date: Optional[date], lead_days: int) -> Optional[date]:
    """
    Calculates due date as `base_date - timedelta(days=lead_days)`.
    Returns None if base_date is missing or invalid.
    """
    if base_date is None:
        return None
    try:
        return base_date - timedelta(days=lead_days)
    except Exception:
        return None
