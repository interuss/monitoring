#!/bin/bash
# USS Qualifier Test Runner with Slack Notification
# This script runs the USS Qualifier tests and sends results to Slack
set -e

# Configuration from environment variables
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/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"
SLACK_BOT_TOKEN="xoxb-4835892069510-9152059209265-oVldazOzj3u0MrFm7RuabxGq"
SLACK_CHANNEL_ID="C094R1ZCH9N"

# SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
# SLACK_BOT_TOKEN="${SLACK_BOT_TOKEN:-}"
# SLACK_CHANNEL_ID="${SLACK_CHANNEL_ID:-}"
TEST_CONFIG="configurations.personal.airwayz_rid_test"

# Use existing output folder for local testing
OUTPUT_DIR="./output/airwayz_rid_test"

# Timestamp for unique artifact naming
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ZIP_FILENAME="test_results_${TIMESTAMP}.zip"
ZIP_PATH="/tmp/${ZIP_FILENAME}"

echo "=== USS Qualifier Test Runner ==="
echo "Config: ${TEST_CONFIG}"
echo "Timestamp: ${TIMESTAMP}"
echo "================================="

cd ..
cd ./monitoring/uss_qualifier

# 1. Run from subdirectory so relative paths in .yaml config work (fixing FileNotFoundError)
# 2. Add repo root to PYTHONPATH so 'monitoring' package is found (fixing ModuleNotFoundError)
export PYTHONPATH="../../"

echo "[INFO] Starting test execution..."
TEST_EXIT_CODE=0
uv run main.py \
    --config "${TEST_CONFIG}" \
    || TEST_EXIT_CODE=$?

echo "[INFO] Test execution completed with exit code: ${TEST_EXIT_CODE}"

# Determine test result status
if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    STATUS=":white_check_mark: SUCCESS"
    COLOR="#36a64f"
else
    STATUS=":x: FAILURE"
    COLOR="#dc3545"
fi

# Create ZIP archive of test results
echo "[INFO] Creating ZIP archive from ${OUTPUT_DIR}..."

# Use PowerShell for zipping on Windows, fall back to zip on Linux
if command -v powershell.exe &> /dev/null; then
    # Windows - use PowerShell
    WIN_OUTPUT=$(cygpath -w "${OUTPUT_DIR}" 2>/dev/null || echo "${OUTPUT_DIR}")
    WIN_ZIP=$(cygpath -w "${ZIP_PATH}" 2>/dev/null || echo "${ZIP_PATH}")
    powershell.exe -Command "Compress-Archive -Path '${WIN_OUTPUT}\\*' -DestinationPath '${WIN_ZIP}' -Force" || true
else
    # Linux - use zip
    cd "${OUTPUT_DIR}"
    zip -r "${ZIP_PATH}" . -x "*.pyc" -x "__pycache__/*" || true
fi

# Get file size (cross-platform)
if [ -f "${ZIP_PATH}" ]; then
    FILE_SIZE=$(wc -c < "${ZIP_PATH}" | tr -d ' ')
    echo "[INFO] Created ZIP: ${ZIP_FILENAME} (${FILE_SIZE} bytes)"
else
    FILE_SIZE=0
    echo "[WARN] Failed to create ZIP file"
fi

# Send notification to Slack
if [ -n "${SLACK_WEBHOOK_URL}" ]; then
    echo "[INFO] Sending Slack notification..."
    
    # Send message via webhook
    PAYLOAD=$(cat <<EOF
{
    "username": "USS Qualifier Bot",
    "icon_emoji": ":robot_face:",
    "attachments": [
        {
            "color": "${COLOR}",
            "title": "USS Qualifier Test Results",
            "fields": [
                {
                    "title": "Status",
                    "value": "${STATUS}",
                    "short": true
                },
                {
                    "title": "Configuration",
                    "value": "${TEST_CONFIG}",
                    "short": true
                },
                {
                    "title": "Timestamp",
                    "value": "${TIMESTAMP}",
                    "short": true
                },
                {
                    "title": "Results Archive",
                    "value": "${ZIP_FILENAME} (${ZIP_SIZE})",
                    "short": true
                }
            ],
            "footer": "USS Qualifier CronJob",
            "ts": $(date +%s)
        }
    ]
}
EOF
)
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "${PAYLOAD}" \
        "${SLACK_WEBHOOK_URL}" \
        && echo "[INFO] Slack notification sent successfully" \
        || echo "[WARN] Failed to send Slack notification"
    
    # Upload ZIP file to Slack using Bot Token (new API)
    if [ -n "${SLACK_BOT_TOKEN}" ] && [ -n "${SLACK_CHANNEL_ID}" ]; then
        echo "[INFO] Uploading ZIP file to Slack..."
        
        FILE_SIZE=$(stat -c%s "/tmp/${ZIP_FILENAME}" 2>/dev/null || stat -f%z "/tmp/${ZIP_FILENAME}")
        
        # Step 1: Get upload URL
        GET_URL_RESPONSE=$(curl -s -X POST \
            -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "filename=${ZIP_FILENAME}&length=${FILE_SIZE}" \
            "https://slack.com/api/files.getUploadURLExternal")
        
        UPLOAD_URL=$(echo "${GET_URL_RESPONSE}" | python -c "import sys, json; print(json.load(sys.stdin).get('upload_url', ''))")
        FILE_ID=$(echo "${GET_URL_RESPONSE}" | python -c "import sys, json; print(json.load(sys.stdin).get('file_id', ''))")
        
        if [ -n "${UPLOAD_URL}" ] && [ -n "${FILE_ID}" ]; then
            # Step 2: Upload file
            curl -s -X POST -F "file=@${ZIP_PATH}" "${UPLOAD_URL}" > /dev/null
            
            # Step 3: Complete upload
            COMPLETE_RESPONSE=$(curl -s -X POST \
                -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
                -H "Content-Type: application/json" \
                -d "{\"files\":[{\"id\":\"${FILE_ID}\",\"title\":\"${ZIP_FILENAME}\"}],\"channel_id\":\"${SLACK_CHANNEL_ID}\",\"initial_comment\":\"USS Qualifier Test Results - ${STATUS}\"}" \
                "https://slack.com/api/files.completeUploadExternal")
            
            IS_OK=$(echo "${COMPLETE_RESPONSE}" | python -c "import sys, json; print(json.load(sys.stdin).get('ok', 'False'))")
            if [ "${IS_OK}" == "True" ]; then
                echo "[INFO] ZIP file uploaded to Slack successfully"
            else
                echo "[WARN] Failed to complete upload: ${COMPLETE_RESPONSE}"
            fi
        else
            echo "[WARN] Failed to get upload URL: ${GET_URL_RESPONSE}"
        fi
    else
        echo "[WARN] SLACK_BOT_TOKEN or SLACK_CHANNEL_ID not set, skipping file upload"
    fi
    
else
    echo "[WARN] SLACK_WEBHOOK_URL not set, skipping Slack notification"
fi

# Print summary
echo ""
echo "=== Test Run Summary ==="
echo "Status: ${STATUS}"
echo "Config: ${TEST_CONFIG}"
echo "Output: ${OUTPUT_DIR}"
echo "Archive: /tmp/${ZIP_FILENAME}"
echo "========================="

# Exit with the test exit code
exit ${TEST_EXIT_CODE}
