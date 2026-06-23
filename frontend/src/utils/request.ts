import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const service = axios.create({
  // 基础路径：直接指向没有 -1 的后端真实域名
  baseURL: import.meta.env.VITE_API_BASE_URL || 'https://xuexipingtai.onrender.com', 
  timeout: 10000 // 请求超时时间
})

// request 拦截器
service.interceptors.request.use(
  config => {
    if (config.url) {
      // 1. 如果写的是全路径（以 http 开头），不需要修改
      if (config.url.startsWith('http')) {
        return config
      }
      
      // 2. 移除最开头的斜杠，方便统一清洗
      let pureUrl = config.url.startsWith('/') ? config.url.slice(1) : config.url
      
      // 3. 彻底防止 /api 重复。如果重复了（比如 api/api/dashboard），就砍掉一个
      if (pureUrl.startsWith('api/api/')) {
        pureUrl = pureUrl.replace('api/api/', 'api/')
      } else if (!pureUrl.startsWith('api/')) {
        // 4. 如果组件写的是 dashboard/stats，自动给他加上 api/ 前缀
        pureUrl = 'api/' + pureUrl
      }
      
      // 5. 重新组装回符合 Axios 标准的带有前导斜杠的 url
      config.url = '/' + pureUrl
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
          // 404 的时候把最终试图请求的完整 URL 打印出来，如果还错，我们一眼就能看出拼成啥样了
          message = `请求地址出错 (404): ${error.config?.baseURL || ''}${error.config?.url || ''}`
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