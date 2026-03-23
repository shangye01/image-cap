import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { UserOrganization, UserProfile } from '@/api/auth'

const USER_STORAGE_KEY = 'auth_user'
const TOKEN_STORAGE_KEY = 'token'
const CURRENT_ORG_STORAGE_KEY = 'current_organization'

function readStoredUser(): UserProfile | null {
  const raw = localStorage.getItem(USER_STORAGE_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as UserProfile
  } catch {
    localStorage.removeItem(USER_STORAGE_KEY)
    return null
  }
}

function readStoredCurrentOrganization() {
  return localStorage.getItem(CURRENT_ORG_STORAGE_KEY) || ''
}

export const useUserStore = defineStore('user', () => {
  const user = ref<UserProfile | null>(readStoredUser())
  const token = ref(localStorage.getItem(TOKEN_STORAGE_KEY) || '')
  const currentOrganizationName = ref(readStoredCurrentOrganization())

  const isLogin = computed(() => Boolean(token.value && user.value))
  const currentOrganization = computed(() => {
    const organizations = user.value?.organizations || []
    if (!organizations.length) return null

    const matched = organizations.find(
      (item) => item.organization_nickname === currentOrganizationName.value,
    )

    return matched || organizations[0]
  })

  function persistUser(userInfo: UserProfile | null) {
    if (!userInfo) {
      localStorage.removeItem(USER_STORAGE_KEY)
      return
    }

    user.value = userInfo
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(userInfo))
  }

  function syncCurrentOrganization() {
    const organizations = user.value?.organizations || []

    if (!organizations.length) {
      currentOrganizationName.value = ''
      localStorage.removeItem(CURRENT_ORG_STORAGE_KEY)
      return
    }

    const exists = organizations.some(
      (item) => item.organization_nickname === currentOrganizationName.value,
    )

    const preferredOrganization =
      organizations.find((item) => item.organization_type === '团队') || organizations[0]
    if (!preferredOrganization) return

    if (!exists) {
      currentOrganizationName.value = preferredOrganization.organization_nickname
    }

    localStorage.setItem(CURRENT_ORG_STORAGE_KEY, currentOrganizationName.value)
  }

  function login(userInfo: UserProfile, tokenStr: string) {
    token.value = tokenStr
    localStorage.setItem(TOKEN_STORAGE_KEY, tokenStr)
    persistUser(userInfo)
    syncCurrentOrganization()
  }

  function setUser(userInfo: UserProfile | null) {
    if (userInfo) {
      persistUser(userInfo)
      syncCurrentOrganization()
      return
    }
    user.value = null
    localStorage.removeItem(USER_STORAGE_KEY)
    currentOrganizationName.value = ''
    localStorage.removeItem(CURRENT_ORG_STORAGE_KEY)
  }

  function setCurrentOrganization(name: string) {
    currentOrganizationName.value = name
    if (name) {
      localStorage.setItem(CURRENT_ORG_STORAGE_KEY, name)
    } else {
      localStorage.removeItem(CURRENT_ORG_STORAGE_KEY)
    }
  }

  function addOrganization(organization: UserOrganization) {
    if (!user.value) return false

    const exists = user.value.organizations.some(
      (item) =>
        item.organization_nickname.toLowerCase() ===
          organization.organization_nickname.toLowerCase() &&
        item.organization_type === organization.organization_type,
    )

    if (exists) {
      throw new Error('团队名称已存在')
    }

    persistUser({
      ...user.value,
      organizations: [...user.value.organizations, organization],
    })
    setCurrentOrganization(organization.organization_nickname)
    return true
  }

  function refreshUserOrganizations(userInfo?: UserProfile) {
    if (userInfo) {
      persistUser(userInfo)
    } else if (user.value) {
      persistUser({
        ...user.value,
        organizations: [...user.value.organizations],
      })
    }
    syncCurrentOrganization()
  }

  function logout() {
    user.value = null
    token.value = ''
    currentOrganizationName.value = ''
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
    localStorage.removeItem(CURRENT_ORG_STORAGE_KEY)
  }

  syncCurrentOrganization()

  return {
    user,
    token,
    isLogin,
    currentOrganizationName,
    currentOrganization,
    login,
    setUser,
    setCurrentOrganization,
    addOrganization,
    refreshUserOrganizations,
    logout,
  }
})
