<template>
  <div class="flex flex-col h-screen bg-[#F5F7FA] text-[#2C3E50] font-sans">
    <!-- 顶部导航栏 -->
    <header class="h-16 bg-[#1A3A5C] text-white flex items-center justify-between px-6 shrink-0 shadow-lg z-50">
      <!-- 左侧 Logo 区域 -->
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 flex items-center justify-center text-[#4A90D9]">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="w-full h-full">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        </div>
        <h1 class="text-lg font-bold tracking-wider">自动气象站智慧学习平台</h1>
      </div>

      <!-- 右侧导航标签 -->
      <nav class="flex items-center gap-1 h-full">
        <router-link 
          v-for="nav in navItems" 
          :key="nav.path"
          :to="nav.path" 
          class="px-5 h-full flex items-center text-sm font-medium transition-all duration-200 hover:bg-white/10"
          :class="[ $route.path === nav.path ? 'bg-white/20 border-b-4 border-[#4A90D9] text-[#4A90D9]' : 'text-white/80' ]"
        >
          {{ nav.name }}
        </router-link>

        <!-- 智能管理入口 -->
        <div class="ml-6 border-l border-white/20 pl-6 h-8 flex items-center">
          <el-dropdown trigger="click">
            <el-button type="primary" class="!bg-[#4A90D9] !border-[#4A90D9] !rounded-full !px-4 !py-1 text-xs">
              智能管理
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/qbank')">智能解析 Docx/PDF 入库</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </nav>
    </header>

    <!-- 主内容区 -->
    <main class="flex-1 overflow-auto p-6">
      <div class="max-w-7xl mx-auto h-full">
        <router-view></router-view>
      </div>
    </main>

    <!-- 悬浮聊天按钮 (组卷入口) -->
    <button 
      class="fixed bottom-8 right-8 w-14 h-14 bg-[#4A90D9] text-white rounded-full shadow-2xl flex items-center justify-center hover:bg-[#357ABD] hover:scale-110 active:scale-95 transition-all duration-300 z-50 group"
      @click="$router.push('/chat')"
    >
      <svg class="w-7 h-7 group-hover:rotate-12 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
      <!-- 提示气泡 -->
      <span class="absolute right-16 bg-[#1A3A5C] text-white text-xs py-1.5 px-3 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-md">
        AI 智能组卷
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ArrowDown } from '@element-plus/icons-vue'

const navItems = [
  { name: '首页', path: '/dashboard' },
  { name: '题库', path: '/qbank' },
  { name: '组卷', path: '/chat' },
  { name: '考试', path: '/exam' },
  { name: '错题本', path: '/wrongbook' }
]
</script>

<style>
/* 重置默认样式 */
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
}
#app {
  width: 100%;
  max-width: none;
  min-height: 100vh;
  display: block;
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #CBD5E0;
  border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
  background: #A0AEC0;
}
</style>
