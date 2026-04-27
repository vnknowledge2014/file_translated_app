#!/bin/bash
# ══════════════════════════════════════════════════════════════
# E2E Live Test Suite — Tests against RUNNING backend
# Requires: Backend running on http://localhost:8000
# ══════════════════════════════════════════════════════════════

BASE_URL="http://localhost:8000"
PASS=0
FAIL=0
TOTAL=0
TEST_USER="e2e_user_$(date +%s)"
TEST_PASS="E2ePass123!"
TOKEN=""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

assert_status() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"
    local body="$4"
    TOTAL=$((TOTAL + 1))
    if [ "$actual" = "$expected" ]; then
        echo -e "  ${GREEN}✅ PASS${NC} [$test_name] — HTTP $actual"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} [$test_name] — Expected HTTP $expected, got $actual"
        echo -e "       Body: ${body:0:200}"
        FAIL=$((FAIL + 1))
    fi
}

echo -e "\n${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  E2E LIVE TEST SUITE — $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${CYAN}  Target: $BASE_URL${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

# ── 1. Health Check ──
echo -e "\n${YELLOW}▸ Phase 1: Health Check${NC}"
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/health")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "Health endpoint responds" "200" "$HTTP_CODE" "$BODY"

STATUS=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
TOTAL=$((TOTAL + 1))
if [ "$STATUS" = "ok" ]; then
    echo -e "  ${GREEN}✅ PASS${NC} [Health status = 'ok']"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC} [Health status expected 'ok', got '$STATUS']"
    FAIL=$((FAIL + 1))
fi

# ── 2. Auth: Register ──
echo -e "\n${YELLOW}▸ Phase 2: User Registration${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "Register new user" "200" "$HTTP_CODE" "$BODY"

USERNAME=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('username',''))" 2>/dev/null)
TOTAL=$((TOTAL + 1))
if [ "$USERNAME" = "$TEST_USER" ]; then
    echo -e "  ${GREEN}✅ PASS${NC} [Returned username matches]"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC} [Username expected '$TEST_USER', got '$USERNAME']"
    FAIL=$((FAIL + 1))
fi

# ── 3. Auth: Duplicate Register ──
echo -e "\n${YELLOW}▸ Phase 3: Duplicate Registration Rejected${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "Duplicate register rejected" "400" "$HTTP_CODE" "$BODY"

# ── 4. Auth: Login ──
echo -e "\n${YELLOW}▸ Phase 4: User Login${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/login" \
    -d "username=$TEST_USER&password=$TEST_PASS")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "Login with correct credentials" "200" "$HTTP_CODE" "$BODY"

TOKEN=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
TOTAL=$((TOTAL + 1))
if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    echo -e "  ${GREEN}✅ PASS${NC} [Got JWT token (${#TOKEN} chars)]"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC} [No token received]"
    FAIL=$((FAIL + 1))
fi

# ── 5. Auth: Login wrong password ──
echo -e "\n${YELLOW}▸ Phase 5: Wrong Password Rejected${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/login" \
    -d "username=$TEST_USER&password=wrong_password")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "Login with wrong password" "400" "$HTTP_CODE" "$BODY"

# ── 6. Auth: /me endpoint ──
echo -e "\n${YELLOW}▸ Phase 6: Authenticated /me Endpoint${NC}"
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/auth/me" \
    -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "/me with valid token" "200" "$HTTP_CODE" "$BODY"

ME_USER=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('username',''))" 2>/dev/null)
TOTAL=$((TOTAL + 1))
if [ "$ME_USER" = "$TEST_USER" ]; then
    echo -e "  ${GREEN}✅ PASS${NC} [/me returns correct username]"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC} [Expected '$TEST_USER', got '$ME_USER']"
    FAIL=$((FAIL + 1))
fi

# ── 7. Protected: Jobs without token ──
echo -e "\n${YELLOW}▸ Phase 7: Protected Endpoints — No Auth${NC}"
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/jobs")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "GET /api/jobs without token → 401/403" "401" "$HTTP_CODE"

# ── 8. Protected: Jobs with token ──
echo -e "\n${YELLOW}▸ Phase 8: Protected Endpoints — With Auth${NC}"
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/jobs" \
    -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "GET /api/jobs with valid token" "200" "$HTTP_CODE" "$BODY"

# ── 9. Upload with auth ──
echo -e "\n${YELLOW}▸ Phase 9: File Upload with Auth${NC}"
# Create a small test docx file (just fake bytes for type detection)
echo "Test document content" > /tmp/e2e_test.txt
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/e2e_test.txt;filename=test_doc.txt")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "Upload .txt file with auth" "200" "$HTTP_CODE" "$BODY"

JOB_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)
TOTAL=$((TOTAL + 1))
if [ -n "$JOB_ID" ] && [ "$JOB_ID" != "" ]; then
    echo -e "  ${GREEN}✅ PASS${NC} [Got job_id: ${JOB_ID:0:20}...]"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ FAIL${NC} [No job_id in response]"
    FAIL=$((FAIL + 1))
fi

# ── 10. Upload without auth ──
echo -e "\n${YELLOW}▸ Phase 10: Upload without Auth Rejected${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/upload" \
    -F "file=@/tmp/e2e_test.txt;filename=test_doc.txt")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "Upload without token → 401/403" "401" "$HTTP_CODE"

# ── 11. IDOR: Access job with different user ──
echo -e "\n${YELLOW}▸ Phase 11: IDOR Prevention — Owner Isolation${NC}"
# Register a second user
ATTACKER="attacker_$(date +%s)"
curl -s -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$ATTACKER\",\"password\":\"Attack123!\"}" > /dev/null

ATKR_RESP=$(curl -s "$BASE_URL/api/auth/login" -X POST \
    -d "username=$ATTACKER&password=Attack123!")
ATK_TOKEN=$(echo "$ATKR_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -n "$JOB_ID" ] && [ -n "$ATK_TOKEN" ]; then
    RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/jobs/$JOB_ID" \
        -H "Authorization: Bearer $ATK_TOKEN")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    assert_status "Attacker accessing victim's job → 403" "403" "$HTTP_CODE"
fi

# ── 12. Expired token ──
echo -e "\n${YELLOW}▸ Phase 12: Expired Token Rejected${NC}"
# Use a known expired token (we can't easily generate one via curl, so use a garbage token)
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/jobs" \
    -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxMDAwMDAwMDAwfQ.invalid")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "Invalid/expired token → 401" "401" "$HTTP_CODE"

# ── 13. Languages endpoint ──
echo -e "\n${YELLOW}▸ Phase 13: Meta Endpoints${NC}"
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/languages")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | head -1)
assert_status "GET /api/languages" "200" "$HTTP_CODE"

RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/domains")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "GET /api/domains" "200" "$HTTP_CODE"

# ── Summary ──
echo -e "\n${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  E2E RESULTS SUMMARY${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "  Total:  $TOTAL"
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"

if [ $FAIL -eq 0 ]; then
    echo -e "\n  ${GREEN}🎉 ALL TESTS PASSED — PRODUCTION READY${NC}"
    exit 0
else
    echo -e "\n  ${RED}⚠️  SOME TESTS FAILED — REVIEW NEEDED${NC}"
    exit 1
fi
