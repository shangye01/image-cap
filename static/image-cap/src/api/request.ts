import axios, { type AxiosRequestConfig } from 'axios'
import { useUserStore } from '@/stores/user'

const service = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

service.interceptors.request.use((config) => {
  const store = useUserStore()

  if (store.token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${store.token}`
  }

  console.log('REQUEST URL =>', config.baseURL, config.url)
  return config
})

service.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
)

const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.get<any, T>(url, config)
  },
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.post<any, T>(url, data, config)
  },
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.put<any, T>(url, data, config)
  },
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.delete<any, T>(url, config)
  },
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.patch<any, T>(url, data, config)
  },
}

export default request