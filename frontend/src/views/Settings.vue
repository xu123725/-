<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-gray-800">系统设置</h2>
    </div>

    <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 max-w-xl mt-10">
      <div class="flex items-center gap-3 mb-6">
        <svg class="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="text-lg font-bold">大模型网关状态</h3>
      </div>
      
      <div class="space-y-4 text-gray-600">
        <p class="text-sm bg-blue-50 text-blue-700 p-3 rounded-lg border border-blue-100">
          {{ configInfo.message || '配置已由后端统一管理' }}
        </p>

        <div class="grid grid-cols-3 gap-4 border-t border-gray-100 pt-4">
          <div class="col-span-1 font-medium text-gray-700">当前模型：</div>
          <div class="col-span-2">{{ configInfo.current_model || '加载中...' }}</div>
        </div>

        <div class="grid grid-cols-3 gap-4 border-t border-gray-100 pt-4">
          <div class="col-span-1 font-medium text-gray-700">API 接口：</div>
          <div class="col-span-2 truncate" :title="configInfo.current_base_url">{{ configInfo.current_base_url || '加载中...' }}</div>
        </div>

        <div class="grid grid-cols-3 gap-4 border-t border-gray-100 pt-4">
          <div class="col-span-1 font-medium text-gray-700">密钥状态：</div>
          <div class="col-span-2 text-green-600 flex items-center">
            <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            已配置并隐藏
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '../utils/request'

const configInfo = ref<any>({})

const fetchSettings = async () => {
  try {
    const data: any = await request.get('/settings/')
    configInfo.value = data
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchSettings()
})
</script>