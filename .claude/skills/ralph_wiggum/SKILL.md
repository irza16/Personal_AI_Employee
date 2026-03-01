# Ralph Wiggum Autonomous Loop Skill

## Description
Implements an autonomous loop that takes a task description and completion condition, creates a state file for tracking, runs Claude Code in a loop, checks completion conditions, and continues until the task is complete or max iterations are reached. This enables persistent autonomous execution until a goal is achieved.

## Inputs
- Task description and completion condition as arguments
- --completion-file flag specifying the file to monitor for completion
- --max-iterations flag (default: 10)
- Previous Claude output as context for next iteration

## Outputs
- Creates state file in Plans/ tracking current iteration
- Runs Claude Code in a loop until completion condition is met
- Logs each iteration to Logs/ralph_wiggum_{task}_{date}.json
- Continues execution until <promise>TASK_COMPLETE</promise> is found or file is moved to Done/
- Stops when complete OR max iterations reached

## Hard Limits
- Must never run indefinitely without max iteration limit
- Must always respect the completion condition check
- Must never execute without proper state tracking
- Must always maintain iteration logs for debugging
- Must never bypass the promise/file-based completion check
- Must always provide a way to terminate the loop