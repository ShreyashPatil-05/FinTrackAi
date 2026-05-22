from django import template

register = template.Library()


@register.filter
def inr(value):
    """Format a number in Indian currency style: ₹1,23,456 / ₹12.3L / ₹1.2Cr"""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value

    abs_val = abs(value)
    sign = '-' if value < 0 else ''

    if abs_val >= 1_00_00_000:
        formatted = f"{abs_val / 1_00_00_000:.2f}".rstrip('0').rstrip('.')
        return f"{sign}₹{formatted}Cr"

    if abs_val >= 1_00_000:
        formatted = f"{abs_val / 1_00_000:.2f}".rstrip('0').rstrip('.')
        return f"{sign}₹{formatted}L"

    # Indian comma grouping: last 3 digits, then groups of 2
    n = str(int(abs_val))
    if len(n) <= 3:
        return f"{sign}₹{n}"

    last3 = n[-3:]
    rest = n[:-3]
    # Group remaining digits in pairs from right
    groups = []
    while len(rest) > 2:
        groups.append(rest[-2:])
        rest = rest[:-2]
    groups.append(rest)
    groups.reverse()
    return f"{sign}₹{','.join(groups)},{last3}"


@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter — e.g. '10,20,50'|split:',' """
    return str(value).split(delimiter)


import json as _json

@register.filter
def json_monthly_labels(monthly_data):
    """Extract month labels from monthly_data for Chart.js"""
    return _json.dumps([f"{m['month'][:3]} {m['year']}" for m in monthly_data])

@register.filter
def json_monthly_income(monthly_data):
    return _json.dumps([m['income'] for m in monthly_data])

@register.filter
def json_monthly_spent(monthly_data):
    return _json.dumps([m['spent'] for m in monthly_data])

@register.filter
def json_monthly_saved(monthly_data):
    return _json.dumps([m['saved'] for m in monthly_data])
