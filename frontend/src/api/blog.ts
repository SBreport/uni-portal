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
  branch_filter?: string
}

export const getBlogPosts = (params?: BlogPostsParams) =>
  api.get('/blog/posts', { params })

export const getBlogPost = (id: number) =>
  api.get(`/blog/posts/${id}`)

export const getBlogFilterOptions = (params?: { branch_filter?: string }) =>
  api.get('/blog/filter-options', { params })

export const getBlogStats = () =>
  api.get('/blog/stats')

export const getBlogDashboard = (params?: { branch_filter?: string; month?: string }) =>
  api.get('/blog/dashboard', { params })

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

export const syncNotion = (token?: string, full: boolean = false) =>
  api.post('/blog/sync-notion', { token: token || null, full })

export const getNotionSyncStatus = () =>
  api.get('/blog/sync-notion/status')

export const getNotionTokenStatus = () =>
  api.get('/blog/notion-token/status')

export const saveNotionToken = (token: string) =>
  api.post('/blog/notion-token', { token })

export const getScrapeTitlesStatus = () =>
  api.get('/blog/scrape-titles/status')

export const scrapeTitles = (params?: { limit?: number; delay?: number; include_cafe?: boolean }) =>
  api.post('/blog/scrape-titles', params || {})

export const importBlogData = () =>
  api.post('/blog/import-data')
