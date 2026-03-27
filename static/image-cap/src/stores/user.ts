import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import type { UserOrganization, UserProfile } from '@/api/auth'
import { jwtDecode } from 'jwt-decode'

const USER_STORAGE_KEY = 'auth_user'
const TOKEN_STORAGE_KEY = 'token'
const CURRENT_ORG_STORAGE_KEY = 'current_organization'

// ========== 辅助函数 ==========

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

function readStoredCurrentOrganization(): string {
  return localStorage.getItem(CURRENT_ORG_STORAGE_KEY) || ''
}

/** 检查 token 是否过期 */
function isTokenExpired(token: string): boolean {
  try {
    const decoded: { exp?: number } = jwtDecode(token)
    if (!decoded.exp) return true
    return decoded.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

/** 获取有效的初始 token */
function getValidInitialToken(): string {
  const stored = localStorage.getItem(TOKEN_STORAGE_KEY) || ''
  
  if (!stored) return ''
  
  if (isTokenExpired(stored)) {
    // Token 过期，清理所有相关存储
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
    localStorage.removeItem(CURRENT_ORG_STORAGE_KEY)
    console.log('[Auth] Token 已过期，自动清理')
    return ''
  }
  
  return stored
}

// ========== Store 定义 ==========

export const useUserStore = defineStore('user', () => {
  // 使用清理后的有效 token 初始化
  const validInitialToken = getValidInitialToken()
  
  const user = ref<UserProfile | null>(validInitialToken ? readStoredUser() : null)
  const token = ref(validInitialToken)
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

  // ========== 多标签页同步 ==========
  
  if (typeof window !== 'undefined') {
    window.addEventListener('storage', (e) => {
      // Token 变化同步
      if (e.key === TOKEN_STORAGE_KEY) {
        const newToken = e.newValue || ''
        
        // 如果新 token 过期，也清理
        if (newToken && isTokenExpired(newToken)) {
          token.value = ''
          user.value = null
          localStorage.removeItem(TOKEN_STORAGE_KEY)
          localStorage.removeItem(USER_STORAGE_KEY)
          console.log('[Auth] 其他标签页的 Token 已过期，已清理')
          return
        }
        
        token.value = newToken
        if (!newToken) {
          user.value = null
          currentOrganizationName.value = ''
        }
      }
      
      // 用户信息变化同步
      if (e.key === USER_STORAGE_KEY) {
        user.value = e.newValue ? JSON.parse(e.newValue) : null
      }
      
      // 当前组织变化同步
      if (e.key === CURRENT_ORG_STORAGE_KEY) {
        currentOrganizationName.value = e.newValue || ''
      }
    })
  }

  // ========== Actions ==========

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

  /** 登录：保存 token 和用户信息 */
  function login(userInfo: UserProfile, tokenStr: string) {
    // 检查新 token 是否有效
    if (isTokenExpired(tokenStr)) {
      console.error('[Auth] 登录失败：Token 已过期')
      throw new Error('登录凭证已过期，请重新登录')
    }
    
    token.value = tokenStr
    localStorage.setItem(TOKEN_STORAGE_KEY, tokenStr)
    persistUser(userInfo)
    syncCurrentOrganization()
  }

  /** 更新用户信息（不修改 token） */
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

  /** 退出登录：清理所有状态 */
  function logout() {
    user.value = null
    token.value = ''
    currentOrganizationName.value = ''
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
    localStorage.removeItem(CURRENT_ORG_STORAGE_KEY)
  }

  /** 刷新 token（用于续期） */
  function refreshToken(newToken: string) {
    if (isTokenExpired(newToken)) {
      console.error('[Auth] 刷新失败：新 Token 已过期')
      logout()
      return false
    }
    
    token.value = newToken
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken)
    return true
  }

  /** 获取当前有效 token（供外部使用） */
  function getValidToken(): string | null {
    if (!token.value) return null
    if (isTokenExpired(token.value)) {
      logout()
      return null
    }
    return token.value
  }

  // 初始化组织
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
    refreshToken,
    getValidToken,
  }
})