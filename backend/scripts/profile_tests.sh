#!/bin/bash
#
# Profile test execution times to identify bottlenecks
# Usage: ./scripts/profile_tests.sh
#

set -e

echo "Test Module Profiling Report"
echo "============================="
echo ""
echo "Running fast+unit tagged tests module by module..."
echo ""

# Find all test modules
TEST_MODULES=$(find . -name "test_*.py" -path "*/tests/*" -not -path "*/.venv/*" -not -path "*/migrations/*" | \
    xargs -I {} dirname {} | sort -u | sed 's|^\./||')

# Output file for results
RESULTS_FILE="test_timing_results.txt"
> "$RESULTS_FILE"

for module in $TEST_MODULES; do
    # Convert path to Python module notation
    python_module=$(echo "$module" | tr '/' '.')

    echo "Testing: $python_module"

    # Run tests and capture timing
    start_time=$(date +%s.%N)

    docker-compose exec -T backend uv run python manage.py test \
        "$python_module" \
        --tag=fast \
        --tag=unit \
        --keepdb \
        -v 0 \
        2>&1 | grep -E "Ran [0-9]+ test" || echo "0 tests"

    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)

    printf "%-60s %.2fs\n" "$python_module" "$duration" | tee -a "$RESULTS_FILE"
done

echo ""
echo "============================="
echo "Top 20 Slowest Test Modules:"
echo "============================="
sort -t' ' -k2 -rn "$RESULTS_FILE" | head -20

echo ""
echo "Full results saved to: $RESULTS_FILE"
