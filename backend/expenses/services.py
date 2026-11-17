import re

from django.db.models import Q

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
        (
            "travel", "train", "flight", "hotel", "trip", "vacation",
            "cab", "taxi", "uber", "ola", "rapido",
        ),
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
            "electronics", "purchase", "retail", "blinkit", "zepto",
        ),
    ),
    (
        "Healthcare",
        (
            "healthcare", "health", "pharmacy", "medicine", "doctor",
            "hospital", "medical",
        ),
    ),
    (
        "Entertainment",
        ("entertainment", "netflix", "movie", "concert", "streaming"),
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


def suggest_categories(description, user=None, merchant=""):
    """Return history matches first, followed by matching global rule categories."""
    suggestions = []
    seen_ids = set()

    description = description.strip() if isinstance(description, str) else ""
    merchant = merchant.strip() if isinstance(merchant, str) else ""
    tokens = _tokens(" ".join(value for value in (description, merchant) if value))
    if user is not None and (description or merchant):
        history_conditions = []
        if description:
            history_conditions.append(Q(expenses__description__iexact=description))
        if merchant:
            history_conditions.append(Q(expenses__merchant__iexact=merchant))
        history_match = history_conditions[0]
        for condition in history_conditions[1:]:
            history_match |= condition
        history = (
            Category.objects.filter(
                expenses__owner=user,
                expenses__is_deleted=False,
                expenses__category__is_active=True,
            )
            .filter(history_match)
            .distinct()
        )
        history = history.order_by("-expenses__updated_at", "-id")
        for category in history:
            if category.pk not in seen_ids:
                suggestions.append(category)
                seen_ids.add(category.pk)

    if tokens:
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
        for name in category_names:
            category = categories_by_name.get(name)
            if category is not None and category.pk not in seen_ids:
                suggestions.append(category)
                seen_ids.add(category.pk)

    return suggestions
