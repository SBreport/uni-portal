import api from './client'

export const getPlaceMonths = () => api.get('/place/months')

export const getPlaceRanking = (month: string) =>
  api.get('/place/ranking', { params: { month } })
