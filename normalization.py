"""Conservative review-time normalization. Never infer an event date from a feed date.

CLI: python normalization.py state "Uttar-Pradesh"
     python normalization.py date "February 2025"
Results retain raw values and unresolved inputs. No production row is changed.
"""
import argparse
import difflib
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from date_rules import date_bounds

STATES = ('Andhra Pradesh|Arunachal Pradesh|Assam|Bihar|Chhattisgarh|Goa|Gujarat|Haryana|'
          'Himachal Pradesh|Jharkhand|Karnataka|Kerala|Madhya Pradesh|Maharashtra|Manipur|'
          'Meghalaya|Mizoram|Nagaland|Odisha|Punjab|Rajasthan|Sikkim|Tamil Nadu|Telangana|'
          'Tripura|Uttar Pradesh|Uttarakhand|West Bengal').split('|')
IST = timezone(timedelta(hours=5, minutes=30))
MISSING = {'', 'unknown', 'not known', 'not available', 'n/a', 'na', 'null', 'none', '-', '--', 'tbd'}

def clean(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(value or '')).strip())

def state_key(value):
    return re.sub(r'[^a-z]', '', clean(value).casefold())

ALIASES = {state_key(s): s for s in STATES}
for canonical, aliases in {
    'Andhra Pradesh': ['AP'], 'Uttar Pradesh': ['UP'], 'Madhya Pradesh': ['MP'],
    'Tamil Nadu': ['TN'], 'Telangana': ['TG', 'TS', 'Telengana'],
    'Karnataka': ['KA', 'Karnatka'], 'Maharashtra': ['MH', 'Maharastra'],
    'Odisha': ['OD', 'Orissa', 'Odissa'], 'Uttarakhand': ['Uttaranchal'],
    'West Bengal': ['WB'], 'Gujarat': ['GJ'], 'Kerala': ['KL'],
}.items():
    for alias in aliases: ALIASES[state_key(alias)] = canonical

def normalize_state(value):
    """Only call on a structured state field, never arbitrary prose containing 'up'."""
    raw = value
    text = clean(value)
    key = state_key(text)
    result = {'raw': raw, 'value': None, 'status': 'needs_review', 'method': None, 'suggestions': []}
    if text.casefold() in MISSING:
        return dict(result, status='missing', method='missing_marker')
    # ASCII-only mapping avoids silently stripping non-Latin names into unrelated aliases.
    if any(c.isalpha() and not c.isascii() for c in text): return result
    if key in ALIASES:
        canonical = ALIASES[key]
        return dict(result, value=canonical, status='normalized',
                    method='canonical' if text == canonical else 'explicit_alias_or_format')
    suggestions = difflib.get_close_matches(key, [state_key(s) for s in STATES], n=3, cutoff=.78)
    return dict(result, suggestions=[ALIASES[s] for s in suggestions])

def normalize_date(value, *, numeric_order=None, anchor=None):
    """Parse a date field. Ambiguous numeric order requires a declared source convention.

    anchor is an explicit local calendar date for yesterday/today. Approximate phrases
    remain unresolved. Bounds are indexing intervals, not evidence of an exact day.
    """
    raw = value
    text = clean(value)
    result = dict(raw=raw, value=None, precision='unknown', lower_bound=None, upper_bound=None,
                  status='needs_review', method=None, reason='unsupported_or_approximate',
                  numeric_order=numeric_order, anchor=anchor)
    if numeric_order not in (None, 'dayfirst', 'monthfirst'): raise ValueError('Invalid numeric order')
    def accepted(value, precision, method):
        low, high = date_bounds(value, precision)
        return dict(result, value=value, precision=precision, lower_bound=low, upper_bound=high,
                    status='normalized', method=method, reason=None)
    if text.casefold() in MISSING: return dict(result, status='missing', method='missing_marker', reason=None)
    if re.search(r'\b(about|around|approximately|circa|early|mid|late|last|next)\b', text, re.I):
        return result
    try:
        if text.casefold() in ('today', 'yesterday'):
            if not anchor: return dict(result, reason='relative_date_without_anchor')
            day = date.fromisoformat(anchor) - timedelta(days=text.casefold() == 'yesterday')
            return accepted(day.isoformat(), 'day', 'explicit_relative_anchor')
        if re.fullmatch(r'\d{4}(-\d{2}){0,2}', text):
            precision = {4:'year', 7:'month', 10:'day'}[len(text)]
            return accepted(text, precision, 'iso_calendar')
        if re.match(r'^\d{4}-\d\d-\d\d[T ]\d', text):
            stamp = datetime.fromisoformat(text.replace('Z', '+00:00'))
            if stamp.tzinfo is None: return dict(result, reason='timestamp_without_timezone')
            return accepted(stamp.astimezone(IST).date().isoformat(), 'day', 'timestamp_to_IST')
        if re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),', text):
            stamp = parsedate_to_datetime(text)
            if stamp.tzinfo is None: return dict(result, reason='timestamp_without_timezone')
            return accepted(stamp.astimezone(IST).date().isoformat(), 'day', 'rfc2822_to_IST')
        numeric = re.fullmatch(r'(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})', text)
        if numeric:
            a,b,y = map(int, numeric.groups())
            if not numeric_order and a <= 12 and b <= 12 and a != b:
                return dict(result, reason='ambiguous_numeric_date')
            if numeric_order == 'monthfirst' or (not numeric_order and b > 12): a,b = b,a
            return accepted(date(y,b,a).isoformat(), 'day', 'numeric_'+(numeric_order or 'unambiguous'))
        text = re.sub(r'(\d)(st|nd|rd|th)\b', r'\1', text, flags=re.I).replace(',', '')
        for fmt, precision in [('%d %B %Y','day'), ('%d %b %Y','day'), ('%B %d %Y','day'),
                               ('%b %d %Y','day'), ('%B %Y','month'), ('%b %Y','month')]:
            try: parsed = datetime.strptime(text, fmt).date()
            except ValueError: continue
            return accepted(parsed.isoformat()[:7] if precision == 'month' else parsed.isoformat(), precision, 'named_month')
    except (ValueError, TypeError, OverflowError):
        return dict(result, reason='invalid_date')
    return result

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('field', choices=['state','date']); parser.add_argument('value')
    parser.add_argument('--numeric-order', choices=['dayfirst','monthfirst']); parser.add_argument('--anchor')
    args=parser.parse_args()
    print(json.dumps(normalize_state(args.value) if args.field=='state' else normalize_date(args.value,
        numeric_order=args.numeric_order, anchor=args.anchor), ensure_ascii=False, indent=2))
