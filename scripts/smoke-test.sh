#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://app.veritas-infra.com}"
EMAIL="${SMOKE_EMAIL:-}"
PASSWORD="${SMOKE_PASSWORD:-}"

pass=0; fail=0

check() {
    local name="$1" status="$2" expected="$3"
    if [[ "$status" == "$expected" ]]; then
        echo "✅ $name"
        pass=$((pass + 1))
    else
        echo "❌ $name (got HTTP $status, expected $expected)"
        fail=$((fail + 1))
    fi
}

echo "Running smoke tests against $BASE_URL..."
echo ""

# Health
STATUS=$(curl -skL -o /dev/null -w '%{http_code}' "$BASE_URL/health")
check "Health endpoint" "$STATUS" "200"

# Ready
STATUS=$(curl -skL -o /dev/null -w '%{http_code}' "$BASE_URL/ready")
check "Ready endpoint" "$STATUS" "200"

# Login
if [[ -n "$EMAIL" && -n "$PASSWORD" ]]; then
    RESPONSE=$(curl -skL -X POST "$BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

    if [[ -n "$TOKEN" ]]; then
        echo "✅ Login"
        pass=$((pass + 1))

        STATUS=$(curl -skL -o /dev/null -w '%{http_code}' \
            -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/auth/me")
        check "Auth /me endpoint" "$STATUS" "200"

        STATUS=$(curl -skL -o /dev/null -w '%{http_code}' \
            -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/projects/")
        check "Projects endpoint" "$STATUS" "200"

        STATUS=$(curl -skL -o /dev/null -w '%{http_code}' \
            -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/professionals/")
        check "Professionals endpoint" "$STATUS" "200"
    else
        echo "❌ Login failed — check SMOKE_EMAIL and SMOKE_PASSWORD"
        fail=$((fail + 1))
    fi
else
    echo "⚠  Skipping auth tests — set SMOKE_EMAIL and SMOKE_PASSWORD to test login"
fi

echo ""
echo "Results: $pass passed, $fail failed"
if [[ $fail -eq 0 ]]; then
    echo ""
    echo "✅ All smoke tests passed. Platform is operational."
    exit 0
else
    echo ""
    echo "❌ $fail smoke test(s) failed."
    exit 1
fi
