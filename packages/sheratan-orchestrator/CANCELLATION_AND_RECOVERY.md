# Job Cancellation and Worker Recovery

This document describes the advanced job cancellation and worker recovery mechanisms implemented in the Sheratan orchestrator.

## Overview

The orchestrator implements cooperative job cancellation and automatic worker recovery to handle:
- Graceful cancellation of running jobs
- Detection and recovery of "zombie" jobs when workers crash
- Safe handling of race conditions during job lifecycle transitions

## Job Lifecycle and State Transitions

### Job States

```
PENDING → RUNNING → COMPLETED
                 ↓
                 FAILED
                 ↓
              RETRYING → PENDING

Any of PENDING, RUNNING can transition to:
                 ↓
             CANCELLED
```

### State Descriptions

- **PENDING**: Job is queued and waiting to be picked up by a worker
- **RUNNING**: Job is currently being executed by a worker
- **COMPLETED**: Job finished successfully
- **FAILED**: Job failed and cannot be retried (max retries exceeded)
- **RETRYING**: Job failed but will be retried
- **CANCELLED**: Job was cancelled by user request

## Heartbeat and Lease Mechanism

### Purpose

The heartbeat mechanism prevents jobs from getting stuck in RUNNING state when workers crash unexpectedly.

### How It Works

1. **Lease Acquisition**: When a worker starts executing a job:
   - Job status changes to RUNNING
   - `worker_id` is set to identify the worker
   - `heartbeat_at` is set to current timestamp
   - `lease_expires_at` is set to current time + lease duration (default: 5 minutes)

2. **Heartbeat Updates**: While job is running:
   - Worker sends heartbeat updates every 30 seconds (configurable)
   - Each heartbeat extends `lease_expires_at` by the lease duration
   - Heartbeat runs in a separate async task

3. **Lease Expiration**: If worker crashes:
   - Heartbeats stop being sent
   - Lease expires when `lease_expires_at` passes
   - Job becomes a "zombie" and is detected by the recovery mechanism

### Configuration

```python
JobManager(
    heartbeat_interval=30,     # Seconds between heartbeats
    lease_duration=300         # Lease duration in seconds (5 minutes)
)
```

## Zombie Job Detection and Recovery

### What is a Zombie Job?

A zombie job is a job in RUNNING state whose lease has expired, indicating:
- The worker crashed or was terminated
- Network partition prevented heartbeat updates
- Worker is unresponsive

### Detection

Zombie detection runs periodically (every poll interval) and looks for jobs where:
- Status is RUNNING
- `lease_expires_at` is not null
- `lease_expires_at` < (current time - grace period)

Grace period (default 60 seconds) prevents false positives from temporary delays.

### Recovery Process

When a zombie job is detected:

1. **Release Lease**: Clear `worker_id`, `heartbeat_at`, and `lease_expires_at`

2. **Retry or Fail**:
   - If `retry_count < max_retries`: Reset to PENDING for retry, increment retry count
   - Otherwise: Mark as FAILED

3. **Logging**: Record the recovery with details about the failed worker

## Cooperative Job Cancellation

### Cancellation Request

Users can cancel jobs via:
```python
job_manager.cancel_job(job_id)
```

### Cancellable States

Jobs can only be cancelled when in:
- PENDING: Job hasn't started yet
- RUNNING: Job is currently executing

Jobs in COMPLETED, FAILED, or CANCELLED states cannot be cancelled.

### Cooperative Cancellation Flow

For RUNNING jobs, cancellation is **cooperative**:

1. **Mark for Cancellation**: Job status changes to CANCELLED in database

2. **Worker Checks**: Running job checks for cancellation at strategic points:
   - Before starting each major operation (crawl, chunk, embed, upsert)
   - After completing operations
   - Periodically during long-running operations

3. **Graceful Shutdown**: When cancellation detected:
   - Current operation completes if safe
   - Job execution stops
   - Lease is released
   - Resources are cleaned up

4. **No Forced Termination**: Workers are NOT forcefully killed, ensuring:
   - No data corruption
   - Proper cleanup of resources
   - Consistent database state

### Example Cancellation Points

```python
# Before starting operation
if await repo.check_cancellation_requested(job_id):
    raise asyncio.CancelledError()

# After operation
if await repo.check_cancellation_requested(job_id):
    raise asyncio.CancelledError()
```

## Race Condition Handling

### Job Acquisition Race

**Scenario**: Multiple workers try to acquire the same pending job

**Solution**: PostgreSQL row-level locking with `SELECT FOR UPDATE SKIP LOCKED`
- First worker acquires lock and gets the job
- Other workers skip the locked row and move to next job
- No duplicate execution

### Cancellation During Execution Race

**Scenario**: Cancellation request arrives while job is executing

**Solution**: Database-level status check
- Job status is authoritative source in database
- Worker checks status at multiple points
- Cancellation takes effect at next checkpoint
- No race between in-memory and database state

### Heartbeat Update Race

**Scenario**: Worker crashes while updating heartbeat

**Solution**: Transaction isolation
- Heartbeat updates are in separate transaction
- If transaction fails, lease will expire normally
- Zombie detection will recover the job

### Lease Expiration During Execution Race

**Scenario**: Job completes just as lease expires

**Solution**: Worker ID verification
- Zombie recovery checks worker_id before recovering
- If job completes normally, lease is released
- Recovery finds no lease to recover
- No double execution

## Worker Shutdown

### Graceful Shutdown Process

When worker receives shutdown signal (SIGTERM, SIGINT):

1. **Stop Accepting Jobs**: Set `is_running = False`

2. **Cancel Heartbeats**: Stop all heartbeat tasks

3. **Wait for Completion**: Give active jobs 30 seconds to complete

4. **Force Cancellation**: After timeout, cancel remaining job tasks

5. **Cleanup Resources**: Close pipeline, database connections, etc.

### Job State After Shutdown

- **Completed Jobs**: Marked as COMPLETED, lease released
- **Incomplete Jobs**: Lease will expire → zombie recovery → retry
- **Cancelled Jobs**: Already marked CANCELLED

## Safety Guarantees

### Data Consistency

- All job state transitions are atomic database operations
- Transaction isolation prevents inconsistent states
- Row-level locking prevents concurrent modifications

### No Job Loss

- Jobs are never deleted during cancellation or recovery
- Failed jobs remain in database for analysis
- Retry mechanism ensures transient failures are handled

### No Duplicate Execution

- Row-level locking prevents multiple workers from acquiring same job
- Worker ID tracking prevents recovery of jobs still running
- Lease mechanism prevents stale workers from continuing after recovery

### Resource Cleanup

- Leases are always released when job completes, fails, or is cancelled
- Heartbeat tasks are cancelled when job completes
- Pipeline resources are properly closed on shutdown

## Monitoring and Observability

### Logging

All important events are logged:
- Job acquisition with worker ID
- Heartbeat updates (debug level)
- Cancellation requests
- Zombie detection and recovery
- Worker shutdown

### Job Status

Check job status including worker information:
```python
status = await job_manager.get_job_status(job_id)
# Returns: status, worker_id, heartbeat_at, lease_expires_at, etc.
```

### Statistics

Job statistics include cancelled and failed jobs:
```python
stats = await repo.get_job_statistics()
# Returns counts by status including: pending, running, completed, failed, cancelled
```

## Configuration Recommendations

### Development
```python
JobManager(
    heartbeat_interval=10,    # Faster detection of issues
    lease_duration=60         # Shorter lease for quick recovery
)
```

### Production
```python
JobManager(
    heartbeat_interval=30,    # Balance between overhead and detection
    lease_duration=300        # 5 minutes allows for temporary issues
)
```

### High-Reliability
```python
JobManager(
    heartbeat_interval=15,    # More frequent heartbeats
    lease_duration=180        # 3 minutes for faster recovery
)
```

## Error Handling

### Heartbeat Failures

If heartbeat update fails:
- Error is logged
- Heartbeat loop continues trying
- If failures persist, lease will eventually expire
- Zombie recovery will handle the job

### Cancellation Check Failures

If cancellation check fails:
- Error is logged
- Job execution continues
- User can retry cancellation
- Zombie recovery will eventually handle stuck jobs

### Recovery Failures

If zombie recovery fails:
- Error is logged
- Job remains in zombie state
- Next recovery cycle will retry
- Manual intervention may be needed if persistent

## Best Practices

### For Job Implementers

1. **Add Cancellation Checks**: Check for cancellation at natural breakpoints
2. **Keep Operations Idempotent**: Jobs may be retried after recovery
3. **Use Timeouts**: Don't let operations hang indefinitely
4. **Clean Up Resources**: Always clean up in finally blocks

### For Operators

1. **Monitor Zombie Jobs**: Alert if zombie count is consistently high
2. **Tune Lease Duration**: Based on typical job duration
3. **Configure Retries**: Balance between resilience and cost
4. **Review Failed Jobs**: Investigate patterns in job failures

### For Users

1. **Cancel Early**: Cancel jobs as soon as you know they're not needed
2. **Check Status**: Monitor job status to detect stuck jobs
3. **Handle Cancellation**: Applications should handle job cancellation gracefully
4. **Retry Failed Jobs**: Review error messages before retrying

## Implementation Details

### Database Fields

New fields added to `jobs` table:
- `worker_id` (string): Unique identifier of worker executing the job
- `heartbeat_at` (timestamp): Last heartbeat time
- `lease_expires_at` (timestamp): When the job lease expires

### Repository Methods

New methods in `JobRepository`:
- `acquire_job_lease()`: Acquire lease for a job
- `release_job_lease()`: Release job lease
- `update_heartbeat()`: Update heartbeat and extend lease
- `get_zombie_jobs()`: Find jobs with expired leases
- `recover_zombie_job()`: Recover a zombie job
- `check_cancellation_requested()`: Check if job is cancelled

### JobManager Methods

New methods in `JobManager`:
- `cancel_job()`: Request cancellation of a job
- `_heartbeat_loop()`: Maintain heartbeat for running job
- `_recover_zombie_jobs()`: Detect and recover zombie jobs

## Testing

Comprehensive tests cover:
- Heartbeat mechanism
- Zombie detection and recovery
- Cooperative cancellation
- Race conditions
- Worker shutdown
- Lease expiration

Run tests with:
```bash
pytest packages/sheratan-orchestrator/tests/test_cancellation_recovery.py
```

## Future Enhancements

Potential improvements:
- Configurable cancellation timeout (force kill after timeout)
- Job dependencies (cancel child jobs when parent is cancelled)
- Priority-based resource allocation (cancel low priority for high priority)
- Distributed worker coordination (prevent split-brain scenarios)
- Advanced monitoring (metrics, alerts, dashboards)
