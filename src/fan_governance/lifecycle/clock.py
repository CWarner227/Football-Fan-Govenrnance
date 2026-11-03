"""Calendar dates are simulated data, never wall-clock time."""

import calendar
from datetime import date, timedelta


def add_months(value: date, months: int) -> date:
    total = value.year * 12 + value.month - 1 + months
    year, month = divmod(total, 12)
    return date(year, month + 1, min(value.day, calendar.monthrange(year, month + 1)[1]))


class SimulationClock:
    def __init__(self, start_date: date, duration_months: int, timestep: str = "monthly"):
        if duration_months < 1 or timestep not in ("daily", "monthly", "yearly"):
            raise ValueError("Clock requires positive duration and daily/monthly/yearly timestep")
        self.start_date, self.duration_months, self.timestep = start_date, duration_months, timestep
        self.end_date = add_months(start_date, duration_months)
        self.end_day = (self.end_date - start_date).days

    def days(self) -> list[int]:
        if self.timestep == "daily":
            return list(range(self.end_day + 1))
        interval = 1 if self.timestep == "monthly" else 12
        return sorted(
            {
                0,
                self.end_day,
                *(
                    (add_months(self.start_date, n) - self.start_date).days
                    for n in range(interval, self.duration_months + 1, interval)
                ),
            }
        )

    def month_at(self, day: int) -> int:
        current = self.start_date + timedelta(days=day)
        months = (current.year - self.start_date.year) * 12 + current.month - self.start_date.month
        if current < add_months(self.start_date, months):
            months -= 1
        return months
