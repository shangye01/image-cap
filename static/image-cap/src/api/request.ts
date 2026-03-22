import axios from 'axios'
import { useUserStore } from '@/stores/user'

const instance = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 请求拦截器
instance.interceptors.request.use((config) => {
  const store = useUserStore()

  if (store.token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${store.token}`
  }

  return config
})

// 响应拦截器
instance.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
)

export default instance

instance.interceptors.request.use((config) => {
  console.log('REQUEST URL =>', config.baseURL, config.url)
  const store = useUserStore()

  if (store.token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${store.token}`
  }

  return config
})