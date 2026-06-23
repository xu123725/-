<template>
  <div class="flex flex-col h-[calc(100vh-64px)] max-w-4xl mx-auto w-full">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-2xl font-bold text-gray-800">智能助手</h2>
      <div class="flex items-center gap-3">
        <el-button link type="info" @click="clearChat" :disabled="isGenerating">
          <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          清空历史
        </el-button>
        <el-tag type="success">就绪</el-tag>
      </div>
    </div>
    
    <div class="flex-1 bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
      <!-- 聊天区域 -->
      <div class="flex-1 p-6 overflow-y-auto bg-gray-50 flex flex-col gap-4" ref="chatBox">
        <div v-if="chatStore.messages.length === 0" class="text-center text-gray-400 mt-20">
          <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p class="text-lg">有什么可以帮您的？</p>
          <p class="text-sm mt-2">您可以尝试输入：组10道单选题</p>
        </div>
        
        <div v-for="(msg, index) in chatStore.messages" :key="index" class="flex" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
          <div 
            class="max-w-[80%] rounded-2xl px-5 py-3 shadow-sm"
            :class="msg.role === 'user' ? 'bg-purple-600 text-white rounded-br-none' : 'bg-white border border-gray-100 text-gray-800 rounded-bl-none'"
          >
            <div v-if="msg.role === 'user'" class="whitespace-pre-wrap">{{ msg.content }}</div>
            <div v-else class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
      </div>
      
      <!-- 输入框 -->
      <div class="p-4 bg-white border-t border-gray-100">
        <div class="flex gap-2">
          <el-input 
            v-model="inputMsg" 
            placeholder="输入问题或指令（如：组10道单选题）..." 
            @keyup.enter="sendMessage"
            :disabled="isGenerating"
          />
          <el-button 
            type="primary" 
            class="!bg-purple-600 !border-purple-600" 
            @click="sendMessage"
            :loading="isGenerating"
          >
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { useChatStore } from '../store/chat'

const chatStore = useChatStore()
const inputMsg = ref('')
const isGenerating = ref(false)
const chatBox = ref<HTMLElement | null>(null)

// 自动滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (chatBox.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight
  }
}

watch(() => chatStore.messages, scrollToBottom, { deep: true })
onMounted(scrollToBottom)

const clearChat = () => {
  chatStore.clearHistory()
}

const renderMarkdown = (text: string) => {
  marked.setOptions({
    highlight: function (code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext'
      return hljs.highlight(code, { language }).value
    }
  })
  return DOMPurify.sanitize(marked.parse(text) as string)
}

const sendMessage = async () => {
  const content = inputMsg.value.trim()
  if (!content || isGenerating.value) return
  
  // 暂存用于发送历史的副本
  const historyToSend = [...chatStore.messages]
  
  // 添加用户消息到 Store
  chatStore.addMessage({ role: 'user', content })
  inputMsg.value = ''
  isGenerating.value = true
  
  // 添加一个空的助手消息占位
  chatStore.addMessage({ role: 'assistant', content: '' })
  
  try {
    const response = await fetch('http://localhost:8000/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: historyToSend
      })
    })

    if (!response.ok) throw new Error(`HTTP Error: ${response.status}`)
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder('utf-8')
    
    if (!reader) throw new Error('Failed to get stream reader')
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            chatStore.appendToLastMessage(data.content)
            scrollToBottom()
          } catch (e) {
            console.error('JSON Parse error for chunk:', line, e)
          }
        }
      }
    }
  } catch (e: any) {
    chatStore.updateLastMessage(`[请求异常: ${e.message}]`)
  } finally {
    isGenerating.value = false
  }
}
</script>

<style>
.markdown-body {
  font-size: 14px;
  line-height: 1.6;
}
.markdown-body p {
  margin-bottom: 0.5em;
}
.markdown-body p:last-child {
  margin-bottom: 0;
}
.markdown-body pre {
  background-color: #f6f8fa;
  border-radius: 6px;
  padding: 12px;
  overflow: auto;
  margin: 8px 0;
}
.markdown-body code {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 85%;
  background-color: rgba(175, 184, 193, 0.2);
  padding: 0.2em 0.4em;
  border-radius: 6px;
}
.markdown-body pre code {
  background-color: transparent;
  padding: 0;
}
</style>
