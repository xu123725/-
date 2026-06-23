import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const service = axios.create({
  // 💥【终极改动】直接写死真实后端域名，不让任何地方的环境变量干扰它
  baseURL: 'https://xuexipingtai.onrender.com', 
  timeout: 10000 // 请求超时时间
})

// request 拦截器
service.interceptors.request.use(
  config => {
    if (config.url) {
      // 如果已经是绝对路径，不作处理
      if (config.url.startsWith('http')) {
        return config
      }
      
      // 去除开头的斜杠
      let urlPath = config.url.startsWith('/') ? config.url.slice(1) : config.url
      
      // 强力去重：防止出现 api/api 
      if (urlPath.startsWith('api/api/')) {
        urlPath = urlPath.replace('api/api/', 'api/')
      } else if (!urlPath.startsWith('api/')) {
        // 如果组件中没加 api/，强行帮它补上
        urlPath = 'api/' + urlPath
      }
      
      config.url = '/' + urlPath
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
          message = `请求地址出错 (404): ${error.config?.baseURL || ''}${error.config?.url || ''}`
          break
        case 500:
          message = error.response.data?.detail || '服务器内部错误'
          break
        default:
          message = `连接错误 (${error.response.status})`
      }
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