import re

from .models import Category


# The order of this tuple is the deterministic suggestion priority. These
# names match the global categories seeded by the expenses migration.
CATEGORY_RULES = (
    (
        "Food",
        (
            "food", "lunch", "dinner", "cafe", "coffee", "snacks",
            "swiggy", "zomato", "restaurant", "meal",
        ),
    ),
    (
        "Travel",
        ("travel", "train", "flight", "hotel", "trip", "vacation", "cab", "taxi"),
    ),
    (
        "Bills",
        (
            "bill", "electricity", "broadband", "internet", "mobile",
            "recharge", "gas", "utility", "utilities",
        ),
    ),
    (
        "Shopping",
        (
            "shopping", "shop", "amazon", "clothing", "clothes",
            "electronics", "purchase", "retail",
        ),
    ),
    (
        "Healthcare",
        (
            "healthcare", "health", "pharmacy", "medicine", "doctor",
            "hospital", "medical",
        ),
    ),
)


def _tokens(description):
    if not isinstance(description, str):
        return []
    normalized = re.sub(r"[^a-z0-9]+", " ", (description or "").lower())
    return normalized.split()


def _contains_keyword(tokens, keyword):
    keyword_tokens = keyword.split()
    width = len(keyword_tokens)
    return any(
        tokens[index:index + width] == keyword_tokens
        for index in range(len(tokens) - width + 1)
    )


def suggest_categories(description):
    """Return matching active global categories in the configured rule order."""
    tokens = _tokens(description)
    if not tokens:
        return []

    category_names = [
        name
        for name, keywords in CATEGORY_RULES
        if any(_contains_keyword(tokens, keyword) for keyword in keywords)
    ]
    categories = Category.objects.filter(
        owner__isnull=True,
        is_active=True,
        name__in=category_names,
    )
    categories_by_name = {category.name: category for category in categories}
    return [
        categories_by_name[name]
        for name in category_names
        if name in categories_by_name
    ]
