import api from './client'

export interface BlogPostsParams {
  page?: number
  per_page?: number
  channel?: string
  platform?: string
  post_type?: string
  blog_id?: string
  keyword?: string
  search?: string
  date_from?: string
  date_to?: string
  author?: string
}

export const getBlogPosts = (params?: BlogPostsParams) =>
  api.get('/blog/posts', { params })

export const getBlogPost = (id: number) =>
  api.get(`/blog/posts/${id}`)

export const getBlogFilterOptions = () =>
  api.get('/blog/filter-options')

export const getBlogStats = () =>
  api.get('/blog/stats')

export const uploadBlogCsv = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/blog/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
