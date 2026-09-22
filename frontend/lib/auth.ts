'use client'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

export function setToken(token: string): void {
  localStorage.setItem('token', token)
}

export function removeToken(): void {
  localStorage.removeItem('token')
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('refresh_token')
}

export function setRefreshToken(token: string): void {
  localStorage.setItem('refresh_token', token)
}

export function removeRefreshToken(): void {
  localStorage.removeItem('refresh_token')
}

export function setTokenPair(accessToken: string, refreshToken: string): void {
  setToken(accessToken)
  setRefreshToken(refreshToken)
}

export function clearAuth(): void {
  removeToken()
  removeRefreshToken()
}

export function isAuthenticated(): boolean {
  return !!getToken()
}
