import {
  acceptTeamInvitationApi,
  createTeamInvitationApi,
  getTeamInvitationApi,
  type TeamInvitationRecord,
  type UserProfile,
} from '@/api/auth'

export type { TeamInvitationRecord }

export function createTeamInvite(params: { organization_nickname: string }) {
  return createTeamInvitationApi(params)
}

export function getInvitationByToken(token: string) {
  return getTeamInvitationApi(token)
}

export function isInvitationExpired(invitation: TeamInvitationRecord) {
  return new Date(invitation.expires_at).getTime() < Date.now()
}

export function acceptTeamInvitation(token: string, _user: UserProfile) {
  return acceptTeamInvitationApi(token)
}
