import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const user = ref<{ id: number; username: string } | null>(null)
  const token = ref(localStorage.getItem('token') || '')

  const isLogin = computed(() => !!token.value)

  function login(userInfo: { id: number; username: string }, tokenStr: string) {
  user.value = userInfo
  token.value = tokenStr
  localStorage.setItem('token', tokenStr) // 同步保存 token
}


  function logout() {
    user.value = null
    token.value = ''
    localStorage.removeItem('token')
  }

  return { user, token, isLogin, login, logout }
})
