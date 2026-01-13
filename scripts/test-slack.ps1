# Test Slack integration locally
# Run this from PowerShell to verify Slack notification works

$SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"
$SLACK_BOT_TOKEN = "xoxb-4835892069510-9152059209265-oVldazOzj3u0MrFm7RuabxGq"
$SLACK_CHANNEL_ID = "C094R1ZCH9N"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$status = ":white_check_mark: TEST SUCCESS"
$color = "#36a64f"

Write-Host "=== Testing Slack Integration ===" -ForegroundColor Cyan

# Test 1: Send webhook message
Write-Host "`n[1] Sending webhook message..." -ForegroundColor Yellow

$payload = @{
    username    = "USS Qualifier Bot"
    icon_emoji  = ":robot_face:"
    attachments = @(
        @{
            color  = $color
            title  = "USS Qualifier Test Results (TEST MESSAGE)"
            fields = @(
                @{ title = "Status"; value = $status; short = $true }
                @{ title = "Configuration"; value = "configurations.personal.airwayz_rid_test"; short = $true }
                @{ title = "Timestamp"; value = $timestamp; short = $true }
                @{ title = "Results Archive"; value = "test_results_$timestamp.zip"; short = $true }
            )
            footer = "USS Qualifier CronJob - LOCAL TEST"
        }
    )
} | ConvertTo-Json -Depth 5

try {
    $response = Invoke-RestMethod -Uri $SLACK_WEBHOOK_URL -Method Post -Body $payload -ContentType "application/json"
    Write-Host "[OK] Webhook message sent!" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] Webhook error: $_" -ForegroundColor Red
}

# Test 2: Test file upload (zip actual test output)
Write-Host "`n[2] Testing file upload..." -ForegroundColor Yellow

$outputFolder = "..\monitoring\uss_qualifier\output\airwayz_rid_test"
$testZipPath = "$env:TEMP\test_results_$timestamp.zip"
$fileName = "test_results_$timestamp.zip"

# Check if output folder exists
if (Test-Path $outputFolder) {
    Write-Host "Zipping folder: $outputFolder" -ForegroundColor Gray
    Compress-Archive -Path "$outputFolder\*" -DestinationPath $testZipPath -Force
}
else {
    Write-Host "[WARN] Output folder not found: $outputFolder" -ForegroundColor Yellow
    Write-Host "Creating dummy test file instead..." -ForegroundColor Gray
    "This is a test file for Slack upload" | Out-File "$env:TEMP\test_content.txt"
    Compress-Archive -Path "$env:TEMP\test_content.txt" -DestinationPath $testZipPath -Force
    Remove-Item "$env:TEMP\test_content.txt" -ErrorAction SilentlyContinue
}

$headers = @{
    "Authorization" = "Bearer $SLACK_BOT_TOKEN"
}

try {
    # Step 1: Get upload URL from Slack
    $fileSize = (Get-Item $testZipPath).Length
    Write-Host "File size: $fileSize bytes" -ForegroundColor Gray
    
    $getUrlResponse = Invoke-RestMethod -Uri "https://slack.com/api/files.getUploadURLExternal" `
        -Method Post `
        -Headers $headers `
        -Body @{ filename = $fileName; length = $fileSize }
    
    if (-not $getUrlResponse.ok) {
        throw "Failed to get upload URL: $($getUrlResponse.error)"
    }
    
    Write-Host "Got upload URL" -ForegroundColor Gray
    $uploadUrl = $getUrlResponse.upload_url
    $fileId = $getUrlResponse.file_id
    
    # Step 2: Upload file to the URL (using .NET for binary upload)
    Write-Host "Uploading file..." -ForegroundColor Gray
    $fileBytes = [System.IO.File]::ReadAllBytes($testZipPath)
    Invoke-RestMethod -Uri $uploadUrl -Method Post -Body $fileBytes -ContentType "application/octet-stream" | Out-Null
    
    # Step 3: Complete the upload
    Write-Host "Completing upload..." -ForegroundColor Gray
    $completeBody = @{
        files           = @(@{ id = $fileId; title = $fileName })
        channel_id      = $SLACK_CHANNEL_ID
        initial_comment = "USS Qualifier Test Results - $status (LOCAL TEST)"
    } | ConvertTo-Json -Depth 3
    
    $completeResponse = Invoke-RestMethod -Uri "https://slack.com/api/files.completeUploadExternal" `
        -Method Post `
        -Headers $headers `
        -Body $completeBody `
        -ContentType "application/json"
    
    if ($completeResponse.ok) {
        Write-Host "[OK] File uploaded successfully!" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] Upload error: $($completeResponse.error)" -ForegroundColor Red
    }
}
catch {
    Write-Host "[FAIL] Upload error: $_" -ForegroundColor Red
}

# Cleanup
Remove-Item "$env:TEMP\test_content.txt" -ErrorAction SilentlyContinue
Remove-Item $testZipPath -ErrorAction SilentlyContinue

Write-Host "`n=== Check your Slack channel! ===" -ForegroundColor Cyan
