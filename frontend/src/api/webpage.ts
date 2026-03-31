import api from './client'

export const getWebpageMonths = () => api.get('/webpage/months')

export const getWebpageRanking = (month: string) =>
  api.get('/webpage/ranking', { params: { month } })
