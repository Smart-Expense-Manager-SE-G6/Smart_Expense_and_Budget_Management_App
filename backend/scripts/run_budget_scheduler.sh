#!/bin/sh

while :
do
    echo "Running daily budget rollover: $(date)"
    python manage.py rollover_budgets
    echo "Next budget rollover check in 24 hours."
    sleep 86400
done