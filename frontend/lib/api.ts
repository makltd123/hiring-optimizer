import axios, { AxiosError } from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
})

api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let _refreshing = false
let _refreshQueue: Array<(token: string | null) => void> = []

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError) => {
    const original = err.config as any
    if (err.response?.status === 401 && !original._retry && typeof window !== 'undefined') {
      original._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        _clearAndRedirect()
        return Promise.reject(err)
      }

      if (_refreshing) {
        return new Promise((resolve, reject) => {
          _refreshQueue.push((token) => {
            if (token) {
              original.headers.Authorization = `Bearer ${token}`
              resolve(api(original))
            } else {
              reject(err)
            }
          })
        })
      }

      _refreshing = true
      try {
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/refresh`,
          { refresh_token: refreshToken }
        )
        const newToken = data.access_token
        localStorage.setItem('token', newToken)
        if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
        _refreshQueue.forEach((cb) => cb(newToken))
        _refreshQueue = []
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch {
        _refreshQueue.forEach((cb) => cb(null))
        _refreshQueue = []
        _clearAndRedirect()
        return Promise.reject(err)
      } finally {
        _refreshing = false
      }
    }
    return Promise.reject(err)
  }
)

function _clearAndRedirect() {
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
  window.location.href = '/auth/login'
}

export default api
