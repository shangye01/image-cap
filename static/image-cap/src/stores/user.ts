import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { UserProfile } from '@/api/auth'

const USER_STORAGE_KEY = 'auth_user'
const TOKEN_STORAGE_KEY = 'token'

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

export const useUserStore = defineStore('user', () => {
  const user = ref<UserProfile | null>(readStoredUser())
  const token = ref(localStorage.getItem(TOKEN_STORAGE_KEY) || '')

  const isLogin = computed(() => Boolean(token.value && user.value))

  function login(userInfo: UserProfile, tokenStr: string) {
    user.value = userInfo
    token.value = tokenStr
    localStorage.setItem(TOKEN_STORAGE_KEY, tokenStr)
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(userInfo))
  }

  function setUser(userInfo: UserProfile | null) {
    user.value = userInfo
    if (userInfo) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(userInfo))
    } else {
      localStorage.removeItem(USER_STORAGE_KEY)
    }
  }

  function logout() {
    user.value = null
    token.value = ''
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_STORAGE_KEY)
  }

   return { user, token, isLogin, login, setUser, logout }
})
