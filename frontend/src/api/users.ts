import api from './client'

export const getUsers = () => api.get('/users')
export const createUser = (data: {
  username: string
  password: string
  role: string
  branch_id?: number | null
  permissions?: string[]
  memo?: string
}) => api.post('/users', data)
export const deleteUser = (username: string) => api.delete(`/users/${username}`)
export const updateUser = (username: string, data: {
  role?: string
  branch_id?: number | null
  permissions?: string[]
  password?: string
  memo?: string
}) => api.patch(`/users/${username}`, data)
