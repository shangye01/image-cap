const STORAGE_PREFIX = 'task_work_tracker_'
const ACTIVE_WINDOW_MS = 45 * 1000

type TaskTrackerState = {
  taskId: string
  startedAt: number
  lastActivityAt: number
  activeSeconds: number
  saveCount: number
}

function getStorageKey(taskId: string) {
  return `${STORAGE_PREFIX}${taskId}`
}

function readState(taskId: string): TaskTrackerState | null {
  if (!taskId) return null
  const raw = sessionStorage.getItem(getStorageKey(taskId))
  if (!raw) return null

  try {
    return JSON.parse(raw) as TaskTrackerState
  } catch {
    sessionStorage.removeItem(getStorageKey(taskId))
    return null
  }
}

function writeState(state: TaskTrackerState) {
  sessionStorage.setItem(getStorageKey(state.taskId), JSON.stringify(state))
}

function ensureState(taskId: string): TaskTrackerState {
  const existing = readState(taskId)
  if (existing) return existing

  const now = Date.now()
  const state: TaskTrackerState = {
    taskId,
    startedAt: now,
    lastActivityAt: now,
    activeSeconds: 0,
    saveCount: 0,
  }
  writeState(state)
  return state
}

export function startTaskTracking(taskId: string) {
  if (!taskId) return
  ensureState(taskId)
}

export function touchTaskTracking(taskId: string) {
  if (!taskId) return
  const state = ensureState(taskId)
  const now = Date.now()
  const deltaSeconds = Math.max(
    0,
    Math.min(now - state.lastActivityAt, ACTIVE_WINDOW_MS) / 1000,
  )
  state.activeSeconds = Number((state.activeSeconds + deltaSeconds).toFixed(2))
  state.lastActivityAt = now
  writeState(state)
}

export function incrementTaskSaveCount(taskId: string) {
  if (!taskId) return
  const state = ensureState(taskId)
  state.saveCount += 1
  state.lastActivityAt = Date.now()
  writeState(state)
}

export function getTaskTrackingPayload(taskId: string) {
  if (!taskId) return null
  const state = ensureState(taskId)

  return {
    tracker: {
      started_at: new Date(state.startedAt).toISOString(),
      last_activity_at: new Date(state.lastActivityAt).toISOString(),
      work_seconds: Number(state.activeSeconds.toFixed(2)),
      save_count: state.saveCount,
    },
  }
}

export function clearTaskTracking(taskId: string) {
  if (!taskId) return
  sessionStorage.removeItem(getStorageKey(taskId))
}
