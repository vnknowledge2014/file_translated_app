#!/bin/bash
# Multilingual Pipeline E2E Test
# Tests a non-Japanese language pair (German -> English) 
# to verify Model Router and processing pipeline.

BASE_URL="http://127.0.0.1:8000"
TEST_USER="e2e_de_en_user"
TEST_PASS="E2ePass123!"

echo -e "Starting Multilingual E2E Test (DE -> EN)...\n"

# 1. Register / Login to get token
echo "1. Registering/Logging in..."
curl -s -X POST "$BASE_URL/api/auth/register" -H "Content-Type: application/json" -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASS\"}" > /dev/null
LOGIN_RESP=$(curl -s -X POST "$BASE_URL/api/auth/login" -d "username=$TEST_USER&password=$TEST_PASS")
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get auth token"
    exit 1
fi

# 2. Create a test German file
echo "2. Creating test document..."
cat << 'EOF' > /tmp/test_de.txt
Willkommen beim System.
Bitte geben Sie Ihr Passwort ein.
Der Vorgang wurde erfolgreich abgeschlossen.
EOF

# 3. Upload file with DE->EN settings
echo "3. Uploading file for translation (DE -> EN)..."
UPLOAD_RESP=$(curl -s -X POST "$BASE_URL/api/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test_de.txt;filename=test_de.txt" \
    -F "source_lang=de" \
    -F "target_lang=en" \
    -F "domain=general")

JOB_ID=$(echo "$UPLOAD_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)

if [ -z "$JOB_ID" ]; then
    echo "❌ Failed to upload file"
    echo "Response: $UPLOAD_RESP"
    exit 1
fi

echo "✅ Uploaded! Job ID: $JOB_ID"

# 4. Wait for job to complete
echo "4. Waiting for translation to complete..."
for i in {1..30}; do
    JOB_RESP=$(curl -s "$BASE_URL/api/jobs/$JOB_ID" -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo "$JOB_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
    
    echo -ne "\r   Status: $STATUS ($i/30)"
    
    if [ "$STATUS" = "completed" ]; then
        echo -e "\n✅ Translation completed!"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo -e "\n❌ Translation failed!"
        echo "Response: $JOB_RESP"
        exit 1
    fi
    
    sleep 2
done

if [ "$STATUS" != "completed" ]; then
    echo -e "\n❌ Timeout waiting for translation."
    exit 1
fi

# 5. Download and verify
echo "5. Downloading translated file..."
curl -s -o "/tmp/test_en.txt" "$BASE_URL/api/download/$JOB_ID" -H "Authorization: Bearer $TOKEN"

echo "6. Output preview:"
echo "-----------------------------------"
cat /tmp/test_en.txt
echo "-----------------------------------"

echo -e "\n🎉 E2E Test DE->EN passed!"
exit 0
