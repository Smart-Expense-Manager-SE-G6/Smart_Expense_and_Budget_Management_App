from django.db import migrations


DEFAULT_CATEGORIES = ["Food", "Travel", "Bills", "Shopping", "Healthcare"]


def seed_default_categories(apps, schema_editor):
    Category = apps.get_model("expenses", "Category")
    for name in DEFAULT_CATEGORIES:
        category = Category.objects.filter(
            owner__isnull=True,
            name__iexact=name,
        ).first()
        if category is None:
            Category.objects.create(name=name, is_active=True)
        elif not category.is_active:
            category.is_active = True
            category.save(update_fields=["is_active"])


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_categories, migrations.RunPython.noop),
    ]
