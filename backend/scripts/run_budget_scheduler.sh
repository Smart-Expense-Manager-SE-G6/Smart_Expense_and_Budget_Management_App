#!/bin/sh
set -eu

monitoring_dir="${MONITORING_STATE_DIR:-/monitoring}"

record_status() {
    status="$1"
    job="$2"
    message="$3"
    updated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    temp_file="$monitoring_dir/budget-scheduler.json.tmp.$$"
    if ! mkdir -p "$monitoring_dir" \
        || ! printf '{"status":"%s","job":"%s","message":"%s","updated_at":"%s"}\n' \
            "$status" "$job" "$message" "$updated_at" > "$temp_file" \
        || ! mv "$temp_file" "$monitoring_dir/budget-scheduler.json"; then
        echo "WARNING: could not record scheduler monitoring status" >&2
        rm -f "$temp_file" 2>/dev/null || true
    fi
}

# The backend container applies migrations on start; wait for it so the first
# run does not hit missing tables on a fresh database.
record_status "starting" "startup" "Waiting for database migrations."
until python manage.py migrate --check >/dev/null 2>&1
do
    echo "Waiting for database migrations before budget rollover..."
    record_status "starting" "startup" "Waiting for database migrations."
    sleep 5
done

while :
do
    cycle_status="healthy"
    echo "Running daily budget rollover: $(date)"
    record_status "running" "budget-rollover" "Budget rollover is running."
    if python manage.py rollover_budgets; then
        record_status "$cycle_status" "budget-rollover" "Budget rollover completed."
    else
        cycle_status="failed"
        record_status "$cycle_status" "budget-rollover" "Budget rollover failed."
    fi
    echo "Creating due recurring expenses: $(date)"
    record_status "running" "recurring-expenses" "Recurring expense generation is running."
    if python manage.py materialize_recurring_expenses; then
        record_status "$cycle_status" "recurring-expenses" "Recurring expense generation completed."
    else
        cycle_status="failed"
        record_status "$cycle_status" "recurring-expenses" "Recurring expense generation failed."
    fi
    echo "Next scheduler run in 24 hours."
    sleep 86400
done
