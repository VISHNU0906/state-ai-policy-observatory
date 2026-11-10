"""Partial dates remain partial; interval bounds are used only for ordering/filtering."""
import calendar
from datetime import date


def date_bounds(value,precision):
    if precision=='unknown' and not value:return None,None
    if not isinstance(value,str):raise ValueError('Date required for known precision')
    if precision=='day' and len(value)==10:
        day=date.fromisoformat(value);return day.isoformat(),day.isoformat()
    if precision=='month' and len(value)==7:
        day=date.fromisoformat(value+'-01')
        return day.isoformat(),day.replace(day=calendar.monthrange(day.year,day.month)[1]).isoformat()
    if precision=='year' and len(value)==4:
        day=date.fromisoformat(value+'-01-01');return day.isoformat(),day.replace(month=12,day=31).isoformat()
    raise ValueError('Invalid date or precision')


def event_order(event):
    low,high=date_bounds(event.get('event_date'),event['date_precision'])
    return (low is None,-date.fromisoformat(low).toordinal() if low else 0,
            (date.fromisoformat(high)-date.fromisoformat(low)).days if low else 0,event['state'],event['id'])
