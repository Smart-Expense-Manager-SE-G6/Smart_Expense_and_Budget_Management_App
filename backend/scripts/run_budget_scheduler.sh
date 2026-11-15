#!/bin/sh

# The backend container applies migrations on start; wait for it so the first
# run does not hit missing tables on a fresh database.
until python manage.py migrate --check >/dev/null 2>&1
do
    echo "Waiting for database migrations before budget rollover..."
    sleep 5
done

while :
do
    echo "Running daily budget rollover: $(date)"
    python manage.py rollover_budgets
    echo "Creating due recurring expenses: $(date)"
    python manage.py materialize_recurring_expenses
    echo "Next scheduler run in 24 hours."
    sleep 86400
done
