import request from './request'

export interface UserOrganization {
  organization_nickname: string
  organization_type: '个人' | '团队'
  joined_at: string
  member_count: number
  organization_created_at: string
}

export interface UserProfile {
  id: string
  username: string
  avatar: string
  is_active: boolean
  created_at: string
  last_login_at: string | null
  organizations: UserOrganization[]
}

export function loginApi(data: { username: string; password: string }) {
  return request.post<{ access_token: string; user: UserProfile }>('/auth/login', data)
}

export function registerApi(data: {
  username: string
  password: string
  organization_nickname?: string
  organization_type?: '个人' | '团队'
}) {
  return request.post<{ message: string; user: UserProfile }>('/auth/register', data)
}

export function logoutApi() {
  return request.post<{ message: string }>('/auth/logout', {})
}

export function getMeApi() {
  return request.get<{ user: UserProfile }>('/auth/me')
}
