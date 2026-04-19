from datetime import datetime
import pytz
from pytz.exceptions import AmbiguousTimeError, NonExistentTimeError


def convert_to_utc(birth_date: str, birth_time: str, timezone_str: str):
    try:
        local_dt = datetime.strptime(
            f"{birth_date} {birth_time}",
            "%Y-%m-%d %H:%M"
        )
    except ValueError:
        raise ValueError("Invalid date or time format. Use YYYY-MM-DD and HH:MM.")

    try:
        local_tz = pytz.timezone(timezone_str)
    except Exception:
        raise ValueError("Invalid timezone.")

    try:
        localized_dt = local_tz.localize(local_dt, is_dst=None)
    except AmbiguousTimeError:
        raise ValueError(
            "This birth time is ambiguous due to daylight saving time. Try checking the exact recorded birth time."
        )
    except NonExistentTimeError:
        raise ValueError(
            "This birth time does not exist because of a daylight saving time change."
        )

    return localized_dt.astimezone(pytz.utc)