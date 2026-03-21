import axios from 'axios'
import { useUserStore } from '@/stores/user'

const instance = axios.create({
  baseURL: '/api',  // ✅ 改为相对路径，走 Vite 代理
  timeout: 10000,
})


// 请求拦截器
instance.interceptors.request.use(config => {
  const store = useUserStore()
  if (store.token) {
    config.headers.Authorization = `Bearer ${store.token}`
  }
  return config
})

export default instance