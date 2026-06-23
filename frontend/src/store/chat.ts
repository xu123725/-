import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export const useChatStore = defineStore('chat', () => {
  // 从 localStorage 恢复历史，或者默认为空数组
  const savedMessages = localStorage.getItem('chat_history')
  const messages = ref<Message[]>(savedMessages ? JSON.parse(savedMessages) : [])

  const addMessage = (msg: Message) => {
    messages.value.push(msg)
    saveHistory()
  }

  const updateLastMessage = (content: string) => {
    if (messages.value.length > 0) {
      messages.value[messages.value.length - 1].content = content
      saveHistory()
    }
  }

  const appendToLastMessage = (chunk: string) => {
    if (messages.value.length > 0) {
      messages.value[messages.value.length - 1].content += chunk
      saveHistory()
    }
  }

  const clearHistory = () => {
    messages.value = []
    localStorage.removeItem('chat_history')
  }

  const saveHistory = () => {
    localStorage.setItem('chat_history', JSON.stringify(messages.value))
  }

  return {
    messages,
    addMessage,
    updateLastMessage,
    appendToLastMessage,
    clearHistory
  }
})