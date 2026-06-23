<template>
  <div class="space-y-8 max-w-7xl mx-auto py-4">
    <!-- 欢迎区与数据概览 -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      <!-- 问候语 -->
      <div class="lg:col-span-4 pt-4">
        <h2 class="text-3xl font-bold text-[#1A3A5C] mb-2">早安，气象业务员</h2>
        <p class="text-[#2C3E50]/60 text-lg tracking-wide font-medium">今天也是精进业务的一天。</p>
      </div>

      <!-- 数据卡片 -->
      <div class="lg:col-span-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- 已入库题目 -->
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col items-center justify-center transition-all hover:shadow-md">
          <p class="text-4xl font-black text-[#F5A623] mb-2">{{ stats.total_questions || 0 }}</p>
          <p class="text-sm font-bold text-[#2C3E50]/50 tracking-widest uppercase">已入库题目</p>
        </div>
        <!-- 平均正确率 -->
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col items-center justify-center transition-all hover:shadow-md">
          <p class="text-4xl font-black text-[#F5A623] mb-2">{{ (stats.average_accuracy || 0).toFixed(0) }}%</p>
          <p class="text-sm font-bold text-[#2C3E50]/50 tracking-widest uppercase">平均正确率</p>
        </div>
        <!-- 待攻克错题 -->
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col items-center justify-center transition-all hover:shadow-md">
          <p class="text-4xl font-black text-[#F5A623] mb-2">{{ stats.pending_wrong || 0 }}</p>
          <p class="text-sm font-bold text-[#2C3E50]/50 tracking-widest uppercase">待攻克错题</p>
        </div>
      </div>
    </section>

    <!-- 主要功能入口 -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <!-- 模拟考试 -->
      <div 
        @click="$router.push('/exam')" 
        class="bg-[#4A90D9] rounded-3xl p-8 text-white shadow-xl cursor-pointer hover:-translate-y-2 transition-all duration-300 relative overflow-hidden group"
      >
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center mb-6">
            <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-2xl font-bold mb-2">模拟考试</h3>
          <p class="text-white/70">全仿真环境 实时诊断</p>
        </div>
        <div class="absolute -right-8 -bottom-8 opacity-10 group-hover:scale-110 transition-transform duration-500">
          <svg class="w-48 h-48" fill="currentColor" viewBox="0 0 24 24">
             <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      </div>

      <!-- 错误强化 -->
      <div 
        @click="$router.push('/wrongbook')" 
        class="bg-[#F5A623] rounded-3xl p-8 text-white shadow-xl cursor-pointer hover:-translate-y-2 transition-all duration-300 relative overflow-hidden group"
      >
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center mb-6">
            <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="text-2xl font-bold mb-2">错误强化</h3>
          <p class="text-white/70">薄弱环节 针对性巩固</p>
        </div>
        <div class="absolute -right-8 -bottom-8 opacity-10 group-hover:scale-110 transition-transform duration-500">
          <svg class="w-48 h-48" fill="currentColor" viewBox="0 0 24 24">
             <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      </div>

      <!-- 系统设置 -->
      <div 
        @click="$router.push('/settings')" 
        class="bg-[#1A3A5C] rounded-3xl p-8 text-white shadow-xl cursor-pointer hover:-translate-y-2 transition-all duration-300 relative overflow-hidden group"
      >
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center mb-6">
            <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h3 class="text-2xl font-bold mb-2">系统设置</h3>
          <p class="text-white/70">个性化学习 环境配置</p>
        </div>
        <div class="absolute -right-8 -bottom-8 opacity-10 group-hover:scale-110 transition-transform duration-500">
          <svg class="w-48 h-48" fill="currentColor" viewBox="0 0 24 24">
             <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
      </div>
    </section>

    <!-- 底部提示栏 -->
    <section class="bg-[#FFF3E0] rounded-2xl p-5 border border-[#F5A623]/20 shadow-sm flex items-center">
      <div class="w-10 h-10 bg-[#F5A623] rounded-full flex items-center justify-center text-white mr-4 shrink-0">
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p class="text-[#1A3A5C] font-medium">
        智能提醒：最近考试中 <span class="text-[#F5A623] font-bold">“传感器维护”</span> 类题目错误率较高，建议前往“错题强化”重点练习。
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '../utils/request'

const stats = ref<any>({})

onMounted(async () => {
  try {
    const data = await request.get('/dashboard/stats')
    stats.value = data
  } catch (e) {
    console.error('Failed to load stats', e)
  }
})
</script>
