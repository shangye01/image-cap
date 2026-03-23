import type { UserOrganization, UserProfile } from '@/api/auth'

const INVITATION_STORAGE_KEY = 'team_invitation_records'
const ACCEPTED_TEAM_STORAGE_KEY = 'accepted_team_memberships'
const ORGANIZATION_REGISTRY_KEY = 'organization_registry'
const INVITE_EXPIRATION_DAYS = 7

export interface TeamInvitationRecord {
  token: string
  organization_nickname: string
  organization_type: UserOrganization['organization_type']
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
}

interface AcceptedMembershipMap {
  [userId: string]: UserOrganization[]
}

interface OrganizationRegistryRecord {
  organization_nickname: string
  organization_type: UserOrganization['organization_type']
  organization_created_at: string
  owner_id: string
  owner_name: string
}

type OrganizationRegistryMap = Record<string, OrganizationRegistryRecord>

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback

  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function readInvitations() {
  return safeParse<TeamInvitationRecord[]>(localStorage.getItem(INVITATION_STORAGE_KEY), [])
}

function writeInvitations(invitations: TeamInvitationRecord[]) {
  localStorage.setItem(INVITATION_STORAGE_KEY, JSON.stringify(invitations))
}

function readAcceptedMembershipMap() {
  return safeParse<AcceptedMembershipMap>(localStorage.getItem(ACCEPTED_TEAM_STORAGE_KEY), {})
}

function writeAcceptedMembershipMap(map: AcceptedMembershipMap) {
  localStorage.setItem(ACCEPTED_TEAM_STORAGE_KEY, JSON.stringify(map))
}

function readOrganizationRegistry() {
  return safeParse<OrganizationRegistryMap>(localStorage.getItem(ORGANIZATION_REGISTRY_KEY), {})
}

function writeOrganizationRegistry(map: OrganizationRegistryMap) {
  localStorage.setItem(ORGANIZATION_REGISTRY_KEY, JSON.stringify(map))
}

function toOrganizationKey(name: string) {
  return name.trim().toLowerCase()
}

function normalizeOrganization(organization: UserOrganization): UserOrganization {
  return {
    ...organization,
    joined_at: organization.joined_at || new Date().toISOString(),
    organization_created_at: organization.organization_created_at || new Date().toISOString(),
    member_count: Math.max(organization.member_count || 1, 1),
  }
}

function getInviteBaseUrl() {
  if (typeof window === 'undefined') return ''
  return `${window.location.origin}/invite`
}

export function syncOrganizationRegistryFromUser(user: UserProfile | null | undefined) {
  if (!user) return

  const registry = readOrganizationRegistry()
  let hasUpdates = false

  user.organizations.forEach((organization) => {
    if (organization.organization_type !== '团队') return

    const normalized = normalizeOrganization(organization)
    const key = toOrganizationKey(normalized.organization_nickname)
    const previous = registry[key]

    registry[key] = {
      organization_nickname: normalized.organization_nickname,
      organization_type: normalized.organization_type,
      organization_created_at:
        previous?.organization_created_at ||
        normalized.organization_created_at ||
        new Date().toISOString(),
      owner_id: previous?.owner_id || user.id,
      owner_name: previous?.owner_name || user.username,
    }

    hasUpdates = true
  })

  if (hasUpdates) {
    writeOrganizationRegistry(registry)
  }
}

export function mergeAcceptedOrganizations(user: UserProfile | null): UserProfile | null {
  if (!user) return user

  syncOrganizationRegistryFromUser(user)

  const acceptedMap = readAcceptedMembershipMap()
  const acceptedOrganizations = acceptedMap[user.id] || []
  if (!acceptedOrganizations.length) {
    return {
      ...user,
      organizations: user.organizations.map((organization) =>
        withComputedMemberCount(organization),
      ),
    }
  }

  const mergedMap = new Map<string, UserOrganization>()

  user.organizations.forEach((organization) => {
    const normalized = withComputedMemberCount(organization)
    mergedMap.set(toOrganizationKey(normalized.organization_nickname), normalized)
  })

  acceptedOrganizations.forEach((organization) => {
    const normalized = withComputedMemberCount(organization)
    const existing = mergedMap.get(toOrganizationKey(normalized.organization_nickname))
    if (!existing) {
      mergedMap.set(toOrganizationKey(normalized.organization_nickname), normalized)
    }
  })

  return {
    ...user,
    organizations: Array.from(mergedMap.values()),
  }
}

export function createTeamInvite(params: { organization: UserOrganization; inviter: UserProfile }) {
  const organization = normalizeOrganization(params.organization)
  syncOrganizationRegistryFromUser(params.inviter)

  const token = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
  const createdAt = new Date().toISOString()
  const expiresAt = new Date(
    Date.now() + INVITE_EXPIRATION_DAYS * 24 * 60 * 60 * 1000,
  ).toISOString()
  const inviteLink = `${getInviteBaseUrl()}/${token}`

  const record: TeamInvitationRecord = {
    token,
    organization_nickname: organization.organization_nickname,
    organization_type: organization.organization_type,
    organization_created_at: organization.organization_created_at,
    inviter_id: params.inviter.id,
    inviter_name: params.inviter.username,
    invite_link: inviteLink,
    created_at: createdAt,
    expires_at: expiresAt,
    accepted_user_ids: [],
    accepted_members: [],
  }

  const invitations = readInvitations()
  invitations.unshift(record)
  writeInvitations(invitations)
  return record
}

export function listOrganizationInvites(organizationName: string) {
  const key = toOrganizationKey(organizationName)
  return readInvitations().filter((item) => toOrganizationKey(item.organization_nickname) === key)
}

export function getInvitationByToken(token: string) {
  return readInvitations().find((item) => item.token === token) || null
}

export function isInvitationExpired(invitation: TeamInvitationRecord) {
  return new Date(invitation.expires_at).getTime() < Date.now()
}

export function getAcceptedOrganizationsForUser(userId: string) {
  return readAcceptedMembershipMap()[userId] || []
}

export function acceptTeamInvitation(token: string, user: UserProfile) {
  const invitation = getInvitationByToken(token)
  if (!invitation) {
    throw new Error('邀请链接不存在或已失效')
  }

  if (isInvitationExpired(invitation)) {
    throw new Error('邀请链接已过期，请联系团队重新生成')
  }

  const existingOrganization = user.organizations.find(
    (item) =>
      toOrganizationKey(item.organization_nickname) ===
      toOrganizationKey(invitation.organization_nickname),
  )
  if (existingOrganization) {
    return {
      invitation,
      alreadyJoined: true,
      organization: withComputedMemberCount(existingOrganization),
    }
  }

  const acceptedMap = readAcceptedMembershipMap()
  const currentList = acceptedMap[user.id] || []
  const joinedOrganization: UserOrganization = withComputedMemberCount({
    organization_nickname: invitation.organization_nickname,
    organization_type: invitation.organization_type,
    joined_at: new Date().toISOString(),
    member_count: 1,
    organization_created_at: invitation.organization_created_at,
  })

  const alreadyAccepted = currentList.some(
    (item) =>
      toOrganizationKey(item.organization_nickname) ===
      toOrganizationKey(joinedOrganization.organization_nickname),
  )

  if (!alreadyAccepted) {
    acceptedMap[user.id] = [...currentList, joinedOrganization]
    writeAcceptedMembershipMap(acceptedMap)
  }

  const invitations = readInvitations().map((item) => {
    if (item.token !== token) return item

    const acceptedIds = item.accepted_user_ids.includes(user.id)
      ? item.accepted_user_ids
      : [...item.accepted_user_ids, user.id]
    const acceptedMembers = item.accepted_members.some((member) => member.user_id === user.id)
      ? item.accepted_members
      : [...item.accepted_members, { user_id: user.id, username: user.username }]

    return {
      ...item,
      accepted_user_ids: acceptedIds,
      accepted_members: acceptedMembers,
    }
  })
  writeInvitations(invitations)

  return {
    invitation: getInvitationByToken(token) || invitation,
    alreadyJoined: false,
    organization: withComputedMemberCount(joinedOrganization),
  }
}

export function withComputedMemberCount(organization: UserOrganization): UserOrganization {
  const registry = readOrganizationRegistry()
  const key = toOrganizationKey(organization.organization_nickname)
  const baseCount = registry[key] ? 1 : Math.max(organization.member_count || 1, 1)
  const joinedCount = Object.values(readAcceptedMembershipMap()).reduce((count, list) => {
    const hasMembership = list.some((item) => toOrganizationKey(item.organization_nickname) === key)
    return hasMembership ? count + 1 : count
  }, 0)

  return {
    ...organization,
    member_count: Math.max(baseCount + joinedCount, organization.member_count || 1),
  }
}