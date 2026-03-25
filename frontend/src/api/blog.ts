import api from './client'

export interface BlogPostsParams {
  page?: number
  per_page?: number
  channel?: string
  platform?: string
  post_type?: string
  post_type_main?: string
  blog_id?: string
  keyword?: string
  search?: string
  date_from?: string
  date_to?: string
  author?: string
  branch_name?: string
  project_month?: string
  needs_review?: number
}

export const getBlogPosts = (params?: BlogPostsParams) =>
  api.get('/blog/posts', { params })

export const getBlogPost = (id: number) =>
  api.get(`/blog/posts/${id}`)

export const getBlogFilterOptions = () =>
  api.get('/blog/filter-options')

export const getBlogStats = () =>
  api.get('/blog/stats')

export const getBlogDashboard = () =>
  api.get('/blog/dashboard')

export const getBlogAccounts = (params?: { channel?: string; search?: string }) =>
  api.get('/blog/accounts', { params })

export const updateBlogAccount = (blogId: string, data: {
  account_name?: string
  account_group?: string
  channel?: string
  note?: string
}) =>
  api.patch(`/blog/accounts/${blogId}`, data)

export const uploadBlogCsv = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/blog/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
