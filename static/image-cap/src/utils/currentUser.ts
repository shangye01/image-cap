const USER_STORAGE_KEY = 'auth_user'
const TOKEN_STORAGE_KEY = 'token'
const LEGACY_USER_ID_KEY = 'userId'
const LEGACY_TOKEN_KEY = 'authToken'

type StoredUser = {
  id?: string
  username?: string
}

function readStoredUser(): StoredUser | null {
  const raw = localStorage.getItem(USER_STORAGE_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as StoredUser
  } catch {
    return null
  }
}

export function getCurrentUserId(): string {
  return readStoredUser()?.id || localStorage.getItem(LEGACY_USER_ID_KEY) || ''
}

export function getCurrentUsername(): string {
  return readStoredUser()?.username || ''
}

export function getCurrentAuthToken(): string {
  return (
    localStorage.getItem(TOKEN_STORAGE_KEY) ||
    localStorage.getItem(LEGACY_TOKEN_KEY) ||
    ''
  )
}
