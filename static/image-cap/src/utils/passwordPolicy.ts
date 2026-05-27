export const PASSWORD_POLICY_HINT =
  '密码至少 8 位，且必须包含字母和数字；特殊符号可提升安全性；请勿使用常见弱密码。'

export const PASSWORD_POLICY_ITEMS = [
  '长度至少 8 位',
  '至少包含一个字母（大写或小写）',
  '至少包含一个数字',
  '特殊符号可提升安全性，但不是强制',
  '不允许使用常见弱密码',
  '修改密码时不能与最近 3 次使用过的密码重复',
]

const COMMON_WEAK_PASSWORDS = new Set([
  '12345678',
  '123456789',
  '1234567890',
  '87654321',
  '00000000',
  '11111111',
  'aaaaaaaa',
  'abc12345',
  'abcd1234',
  'password',
  'password1',
  'password123',
  'qwertyui',
  'qwerty123',
  'admin123',
  'welcome123',
  'iloveyou',
])

export function validatePasswordPolicy(password: string): string {
  const candidate = password || ''

  if (candidate.length < 8) {
    return '密码长度至少 8 位'
  }

  if (!/[A-Za-z]/.test(candidate)) {
    return '密码至少包含一个字母'
  }

  if (!/\d/.test(candidate)) {
    return '密码至少包含一个数字'
  }

  if (COMMON_WEAK_PASSWORDS.has(candidate.toLowerCase())) {
    return '请勿使用常见弱密码'
  }

  return ''
}
