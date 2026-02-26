# PowerShell script to set up Windows Task Scheduler jobs for AI Employee

# Define paths
$vaultPath = "$PSScriptRoot\AI_Employee_Vault"
$scriptDir = $PSScriptRoot
$orchestratorPath = "$scriptDir\orchestrator.py"
$gmailWatcherPath = "$scriptDir\gmail_watcher.py"
$briefingScriptPath = "$scriptDir\generate_ceo_briefing.py" # This will be created later if needed

Write-Host "Setting up Windows Task Scheduler jobs for AI Employee..." -ForegroundColor Green

# 1. Create task to run orchestrator.py every 5 minutes
$taskNameOrchestrator = "AI_Employee_Orchestrator"
$actionOrchestrator = New-ScheduledTaskAction -Execute "python" -Argument "`"$orchestratorPath`""
$triggerOrchestrator = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 365)
$settingsOrchestrator = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principalOrchestrator = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive

try {
    # Remove existing task if it exists
    Unregister-ScheduledTask -TaskName $taskNameOrchestrator -Confirm:$false -ErrorAction SilentlyContinue

    # Register the new task
    Register-ScheduledTask -TaskName $taskNameOrchestrator -Action $actionOrchestrator -Trigger $triggerOrchestrator -Settings $settingsOrchestrator -Principal $principalOrchestrator -Description "Runs AI Employee Orchestrator every 5 minutes"
    Write-Host "Successfully created task: $taskNameOrchestrator" -ForegroundColor Green
}
catch {
    Write-Host "Failed to create orchestrator task: $_" -ForegroundColor Red
}

# 2. Create task to run gmail_watcher.py at startup and keep it running
$taskNameGmail = "AI_Employee_Gmail_Watcher"
$actionGmail = New-ScheduledTaskAction -Execute "python" -Argument "`"$gmailWatcherPath`""
$triggerGmail = New-ScheduledTaskTrigger -AtStartup
$settingsGmail = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
$principalGmail = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive

try {
    # Remove existing task if it exists
    Unregister-ScheduledTask -TaskName $taskNameGmail -Confirm:$false -ErrorAction SilentlyContinue

    # Register the new task
    Register-ScheduledTask -TaskName $taskNameGmail -Action $actionGmail -Trigger $triggerGmail -Settings $settingsGmail -Principal $principalGmail -Description "Runs Gmail Watcher at startup and keeps it running"
    Write-Host "Successfully created task: $taskNameGmail" -ForegroundColor Green
}
catch {
    Write-Host "Failed to create Gmail watcher task: $_" -ForegroundColor Red
}

# 3. Create task for Sunday 9PM CEO briefing generation
$taskNameBriefing = "AI_Employee_CEO_Briefing"
$actionBriefing = New-ScheduledTaskAction -Execute "python" -Argument "`"$scriptDir\generate_ceo_briefing.py`"" # Placeholder for briefing script

# Set trigger for Sunday at 9 PM
$sunday9PM = (Get-Date -Day ((Get-Date).Day + (7 - (Get-Date).DayOfWeek.value__) % 7)).Date.AddHours(21)
if ($sunday9PM -lt (Get-Date)) {
    $sunday9PM = $sunday9PM.AddDays(7)
}
$triggerBriefing = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 9PM

# Alternative: Create a simpler trigger for testing
$triggerBriefing = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 9PM
$settingsBriefing = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principalBriefing = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive

try {
    # Remove existing task if it exists
    Unregister-ScheduledTask -TaskName $taskNameBriefing -Confirm:$false -ErrorAction SilentlyContinue

    # For now, we'll just create a placeholder task since the briefing script may not exist yet
    # Create a dummy action for now - this would call the briefing generation script
    $dummyAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-Command Write-Host 'CEO Briefing Generation - Placeholder'; python `"$scriptDir\generate_ceo_briefing.py`" 2>`$null"

    # Register the new task
    Register-ScheduledTask -TaskName $taskNameBriefing -Action $dummyAction -Trigger $triggerBriefing -Settings $settingsBriefing -Principal $principalBriefing -Description "Generates CEO briefing every Sunday at 9 PM"
    Write-Host "Successfully created task: $taskNameBriefing" -ForegroundColor Green
}
catch {
    Write-Host "Failed to create CEO briefing task: $_" -ForegroundColor Yellow
    Write-Host "Note: This task may fail if generate_ceo_briefing.py doesn't exist yet" -ForegroundColor Yellow
}

Write-Host "" -ForegroundColor White
Write-Host "Task Setup Complete!" -ForegroundColor Green
Write-Host "Tasks created:" -ForegroundColor Cyan
Write-Host "  - AI_Employee_Orchestrator: Runs every 5 minutes" -ForegroundColor Cyan
Write-Host "  - AI_Employee_Gmail_Watcher: Starts at system startup and restarts if needed" -ForegroundColor Cyan
Write-Host "  - AI_Employee_CEO_Briefing: Runs every Sunday at 9 PM (may need script to be created)" -ForegroundColor Cyan

Write-Host "" -ForegroundColor White
Write-Host "To view tasks: Use Task Scheduler application or run 'Get-ScheduledTask -TaskName AI_Employee_*'" -ForegroundColor Yellow
Write-Host "To run now: Use 'Start-ScheduledTask -TaskName <TaskName>'" -ForegroundColor Yellow
Write-Host "To remove: Use 'Unregister-ScheduledTask -TaskName <TaskName> -Confirm:`$false'" -ForegroundColor Yellow