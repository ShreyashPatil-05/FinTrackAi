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

    if abs_val >= 1_00_00_000:  # 1 crore+
        return f"{sign}₹{abs_val / 1_00_00_000:.2f}Cr".rstrip('0').rstrip('.')
    elif abs_val >= 1_00_000:   # 1 lakh+
        return f"{sign}₹{abs_val / 1_00_000:.2f}L".rstrip('0').rstrip('.')
    else:
        # Indian comma format: 1,23,456
        s = f"{abs_val:,.0f}"
        # Convert western commas to Indian grouping
        parts = s.replace(',', '').split('.')
        n = parts[0]
        if len(n) > 3:
            last3 = n[-3:]
            rest = n[:-3]
            groups = []
            while len(rest) > 2:
                groups.append(rest[-2:])
                rest = rest[:-2]
            if rest:
                groups.append(rest)
            groups.reverse()
            n = ','.join(groups) + ',' + last3
        return f"{sign}₹{n}"


@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter — e.g. '10,20,50'|split:',' """
    return str(value).split(delimiter)
