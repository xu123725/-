import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const service = axios.create({
  // 优先读取你在 .env.production 里配置的变量，如果没有则默认使用此云端后端 API 地址
  baseURL: import.meta.env.VITE_API_BASE_URL || 'https://xuexipingtai.onrender.com', 
  timeout: 10000 // 请求超时时间
})

// request 拦截器
service.interceptors.request.use(
  config => {
    // 可以在这里添加 Token 等认证信息
    return config
  },
  error => {
    console.error('Request Error:', error)
    return Promise.reject(error)
  }
)

// response 拦截器
service.interceptors.response.use(
  response => {
    // 根据后端约定的状态码结构处理
    return response.data
  },
  error => {
    console.error('Response Error:', error)
    let message = '请求错误'
    
    if (error.response) {
      switch (error.response.status) {
        case 400:
          message = error.response.data?.detail || '请求参数错误'
          break
        case 401:
          message = '未授权，请检查 API Key 配置'
          break
        case 403:
          message = '拒绝访问'
          break
        case 404:
          message = '请求地址出错'
          break
        case 408:
          message = '请求超时'
          break
        case 500:
          message = error.response.data?.detail || '服务器内部错误'
          break
        default:
          message = `连接错误 (${error.response.status})`
      }
    } else if (error.message.includes('timeout')) {
      message = '请求超时，请检查网络连接'
    } else if (error.message.includes('Network Error')) {
      message = '网络错误，请检查后端服务是否启动'
    }
    
    ElMessage({
      message,
      type: 'error',
      duration: 5 * 1000
    })
    
    return Promise.reject(error)
  }
)

export default service