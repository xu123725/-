<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-gray-800">模拟考试</h2>
    </div>

    <div v-if="!isExamRunning" class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 max-w-xl mx-auto mt-10">
      <h3 class="text-lg font-bold mb-4">生成模拟试卷</h3>
      
      <el-form label-position="top">
        <el-form-item label="选择题型">
          <el-select v-model="form.question_type" placeholder="所有题型" class="w-full">
            <el-option label="所有题型" value="all" />
            <el-option label="单选题" value="single" />
            <el-option label="填空题" value="fill_blank" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="选择分类">
          <el-select v-model="form.categories" multiple placeholder="所有分类 (不选默认全部)" class="w-full">
            <el-option v-for="cat in availableCategories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>

        <el-form-item label="题目数量">
          <el-input-number v-model="form.limit" :min="1" :max="100" />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.prefer_wrong">优先抽取错题</el-checkbox>
          <el-checkbox v-model="form.prefer_unanswered">优先抽取未做过的题</el-checkbox>
        </el-form-item>

        <el-button type="primary" class="w-full !bg-purple-600 !border-purple-600" @click="startExam" :loading="loading">
          开始考试
        </el-button>
      </el-form>
    </div>

    <div v-else class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
      <div class="flex justify-between items-center mb-6">
        <h3 class="text-xl font-bold">第 {{ currentIndex + 1 }} 题 / 共 {{ questions.length }} 题</h3>
        <el-button @click="exitExam" type="danger" plain>退出考试</el-button>
      </div>

      <div class="mb-8">
        <p class="text-lg text-gray-800 mb-4 whitespace-pre-wrap">{{ currentQuestion.stem }}</p>
        
        <!-- 单选题选项 -->
        <div v-if="currentQuestion.question_type === 'single'" class="space-y-3">
          <div 
            v-for="(opt, idx) in currentQuestion.options" 
            :key="idx"
            @click="selectOption(opt)"
            class="p-3 border rounded-lg cursor-pointer transition-colors"
            :class="[
              userAnswers[currentQuestion.id] === opt 
                ? 'bg-purple-50 border-purple-500 text-purple-700' 
                : 'border-gray-200 hover:bg-gray-50'
            ]"
          >
            {{ opt }}
          </div>
        </div>

        <!-- 填空题 -->
        <div v-else>
          <el-input v-model="userAnswers[currentQuestion.id]" placeholder="请输入你的答案" type="textarea" :rows="3" />
        </div>
      </div>

      <!-- 解析区 (如果已经提交或查看答案) -->
      <div v-if="revealed[currentQuestion.id]" class="p-4 bg-gray-50 rounded-lg mb-6 border border-gray-200">
        <p class="font-bold mb-2">正确答案：<span class="text-green-600">{{ currentQuestion.answer }}</span></p>
        <p class="text-gray-700 whitespace-pre-wrap"><span class="font-bold">解析：</span>{{ currentQuestion.analysis || '暂无解析' }}</p>
      </div>

      <div class="flex justify-between mt-8 border-t pt-4">
        <el-button @click="prevQuestion" :disabled="currentIndex === 0">上一题</el-button>
        <div class="space-x-3">
          <el-button @click="revealAnswer" type="warning" plain :disabled="revealed[currentQuestion.id]">查看答案</el-button>
          <el-button @click="nextQuestion" type="primary" class="!bg-purple-600 !border-purple-600" v-if="currentIndex < questions.length - 1">下一题</el-button>
          <el-button @click="submitExam" type="success" v-else>提交试卷</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const availableCategories = ref<string[]>([])
const loading = ref(false)

const form = ref({
  limit: 10,
  question_type: 'all',
  categories: [],
  prefer_wrong: false,
  prefer_unanswered: false
})

const isExamRunning = ref(false)
const questions = ref<any[]>([])
const currentIndex = ref(0)
const userAnswers = ref<Record<number, string>>({})
const revealed = ref<Record<number, boolean>>({})

const currentQuestion = computed(() => questions.value[currentIndex.value] || {})

const fetchCategories = async () => {
  try {
    const data = await request.get('/qbank/categories')
    availableCategories.value = data.data as string[]
  } catch (e) {
    console.error(e)
  }
}

const startExam = async () => {
  loading.value = true
  try {
    const data: any = await request.post('/exam/generate', form.value)
    if (data.data.length === 0) {
      ElMessage.warning('未能找到符合条件的题目，请调整过滤条件')
      return
    }
    questions.value = data.data
    currentIndex.value = 0
    userAnswers.value = {}
    revealed.value = {}
    isExamRunning.value = true
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const exitExam = () => {
  ElMessageBox.confirm('确定要退出考试吗？当前进度将丢失', '提示', {
    confirmButtonText: '确定退出',
    cancelButtonText: '继续考试',
    type: 'warning'
  }).then(() => {
    isExamRunning.value = false
  }).catch(() => {})
}

const selectOption = (opt: string) => {
  userAnswers.value[currentQuestion.value.id] = opt
}

const prevQuestion = () => {
  if (currentIndex.value > 0) currentIndex.value--
}

const nextQuestion = () => {
  if (currentIndex.value < questions.value.length - 1) currentIndex.value++
}

const logAnswerToBackend = async (questionId: number, isCorrect: boolean) => {
  try {
    await request.post('/qbank/log_answer', {
      question_id: questionId,
      is_correct: isCorrect
    })
  } catch (e) {
    console.error('Failed to log answer', e)
  }
}

const revealAnswer = () => {
  const q = currentQuestion.value
  revealed.value[q.id] = true
  
  // 简单判断正确性
  const userAns = (userAnswers.value[q.id] || '').trim()
  const correctAns = (q.answer || '').trim()
  let isCorrect = false
  
  if (q.question_type === 'single') {
    // 假设选项前缀如 "A. xxx"
    const ansPrefix = correctAns.charAt(0)
    const userPrefix = userAns.charAt(0)
    isCorrect = ansPrefix === userPrefix || userAns === correctAns
  } else {
    isCorrect = userAns === correctAns
  }
  
  logAnswerToBackend(q.id, isCorrect)
}

const submitExam = () => {
  // 把还没揭晓答案的都当做答题完成，进行记录
  questions.value.forEach(q => {
    if (!revealed.value[q.id]) {
      const userAns = (userAnswers.value[q.id] || '').trim()
      const correctAns = (q.answer || '').trim()
      let isCorrect = false
      if (q.question_type === 'single') {
        const ansPrefix = correctAns.charAt(0)
        const userPrefix = userAns.charAt(0)
        isCorrect = ansPrefix === userPrefix || userAns === correctAns
      } else {
        isCorrect = userAns === correctAns
      }
      logAnswerToBackend(q.id, isCorrect)
      revealed.value[q.id] = true
    }
  })
  
  ElMessage.success('试卷已提交，你的答题记录已保存！')
  isExamRunning.value = false
}

onMounted(() => {
  fetchCategories()
})
</script>