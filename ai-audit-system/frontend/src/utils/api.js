import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 审计API
export const getAuditLogs = (params = {}) => api.get('/api/audit/logs', { params })
export const getAuditLogDetail = (id) => api.get(`/api/audit/logs/${id}`)
export const getAuditStats = (days = 30) => api.get('/api/audit/stats/summary', { params: { days } })
export const getDailyStats = (days = 30) => api.get('/api/audit/stats/trends', { params: { days } })
export const getRiskEvents = (params = {}) => api.get('/api/audit/risk/events', { params })
export const getSensitiveDataHits = (params = {}) => api.get('/api/audit/sensitive-data/hits', { params })

// 成本管控API
export const getUserQuotas = (params = {}) => api.get('/api/cost/quotas', { params })
export const getUserQuota = (userId) => api.get(`/api/cost/quotas/${userId}`)
export const updateUserQuota = (userId, data) => api.put(`/api/cost/quotas/${userId}`, data)
export const getUsage = (params = {}) => api.get('/api/cost/usage', { params })
export const getBilling = (params = {}) => api.get('/api/cost/billing', { params })
export const getCostDashboard = () => api.get('/api/cost/dashboard')

// 合规API
export const getComplianceOverview = (days = 30) => api.get('/api/compliance/reports/overview', { params: { days } })
export const getAuditTrail = (params = {}) => api.get('/api/compliance/reports/audit-trail', { params })
export const getGDPRReport = (days = 30) => api.get('/api/compliance/reports/gdpr', { params: { days } })
export const exportComplianceData = (format = 'json') => api.get('/api/compliance/reports/export', { 
  params: { format },
  responseType: format === 'csv' ? 'blob' : 'json'
})
export const getComplianceRules = (params = {}) => api.get('/api/compliance/rules', { params })

// AI代理API
export const chatCompletion = (data) => api.post('/v1/chat/completions', data)
export const listModels = () => api.get('/v1/models')

export default api
