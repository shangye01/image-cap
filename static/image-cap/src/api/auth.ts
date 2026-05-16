import request from './request'

export interface UserOrganization {
  organization_nickname: string
  organization_type: '个人' | '团队'
  joined_at: string
  member_count: number
  organization_created_at: string
}

export interface TeamMember {
  id: string
  name: string
  role: string
  joined_at?: string | null
}

export interface TeamInvitationRecord {
  token: string
  organization_nickname: string
  organization_type: '个人' | '团队'
  organization_created_at: string
  inviter_id: string
  inviter_name: string
  invite_link: string
  created_at: string
  expires_at: string
  accepted_user_ids: string[]
  accepted_members: Array<{
    user_id: string
    username: string
  }>
  accepted_at?: string | null
  accepted_by?: string | null
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

export interface CaptchaPayload {
  captcha_id: string
  image_data: string
  expires_in: number
}

export function getCaptchaApi() {
  return request.get<CaptchaPayload>('/auth/captcha')
}

export function loginApi(data: {
  username: string
  password: string
  captcha_id: string
  captcha_code: string
}) {
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

export function updateUsernameApi(data: { username: string }) {
  return request.put<{ message: string; user: UserProfile }>('/auth/me/username', data)
}

export function changePasswordApi(data: { current_password: string; new_password: string }) {
  return request.put<{ message: string }>('/auth/me/password', data)
}

export function deleteAccountApi(data: { password: string }) {
  return request.delete<{ message: string }>('/auth/me', { data })
}

export function createOrganizationApi(data: {
  organization_nickname: string
  organization_type?: '团队'
}) {
  return request.post<{ message: string; organization: UserOrganization; user: UserProfile }>(
    '/auth/organizations',
    data,
  )
}

export function listOrganizationMembersApi(organizationNickname: string) {
  return request.get<{ organization_nickname: string; members: TeamMember[] }>(
    `/auth/organizations/${encodeURIComponent(organizationNickname)}/members`,
  )
}

export function leaveOrganizationApi(organizationNickname: string) {
  return request.delete<{ message: string; user: UserProfile }>(
    `/auth/organizations/${encodeURIComponent(organizationNickname)}/members/me`,
  )
}

export function createTeamInvitationApi(data: { organization_nickname: string }) {
  return request.post<TeamInvitationRecord>('/auth/team-invitations', data)
}

export function getTeamInvitationApi(token: string) {
  return request.get<TeamInvitationRecord>(`/auth/team-invitations/${encodeURIComponent(token)}`)
}

export function acceptTeamInvitationApi(token: string) {
  return request.post<{
    alreadyJoined: boolean
    organization: UserOrganization
    invitation: TeamInvitationRecord
    user: UserProfile
  }>(`/auth/team-invitations/${encodeURIComponent(token)}/accept`)
}
