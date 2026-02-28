import axios from 'axios'
import { useUserStore } from '@/stores/user'

const instance = axios.create({
  baseURL: 'http://127.0.0.1:8000',  // 开发直接指向 FastAPI
  timeout: 5000,
})

// 请求拦截器：自动带 token
instance.interceptors.request.use(config => {
  const store = useUserStore()
  if (store.token) {
    config.headers.Authorization = `Bearer ${store.token}`
  }
  return config
})

export default instance
