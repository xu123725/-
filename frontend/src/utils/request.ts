import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const service = axios.create({
  // 智能拼接基础路径
  baseURL: import.meta.env.VITE_API_BASE_URL || 'https://xuexipingtai.onrender.com', 
  timeout: 10000 // 请求超时时间
})

// request 拦截器
service.interceptors.request.use(
  config => {
    // 【核心修复：智能路径纠错拦截】
    // 如果组件里传过来的 url 既没有以 /api 开头，也没有以 http 开头
    // 比如只是写了 'dashboard/stats' 或 '/dashboard/stats'
    if (config.url && !config.url.startsWith('/api') && !config.url.startsWith('http')) {
      // 自动帮它补上后端口里必须要求的 /api 前缀
      config.url = config.url.startsWith('/') ? `/api${config.url}` : `/api/${config.url}`
    }
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
          // 打印出具体是哪个合成路径 404 了，方便万一报错时一目了然
          message = `请求地址出错: ${error.config?.url || ''}`
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