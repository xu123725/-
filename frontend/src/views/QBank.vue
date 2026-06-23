<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-gray-800">我的题库</h2>
      <el-upload
        action="http://localhost:8000/api/qbank/upload"
        :show-file-list="false"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        accept=".docx"
      >
        <el-button type="primary" class="!bg-purple-600 !border-purple-600 hover:!bg-purple-700">
          导入 DOCX 题库
        </el-button>
      </el-upload>
    </div>

    <!-- 过滤器 -->
    <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex gap-4">
      <el-select v-model="queryParams.category" placeholder="所有分类" clearable class="w-48" @change="fetchQuestions">
        <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
      </el-select>
      
      <el-select v-model="queryParams.question_type" placeholder="所有题型" clearable class="w-48" @change="fetchQuestions">
        <el-option label="单选题" value="single" />
        <el-option label="填空题" value="fill_blank" />
      </el-select>
    </div>

    <!-- 题目列表 -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <el-table :data="tableData" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="stem" label="题干" show-overflow-tooltip>
          <template #default="scope">
            <span class="font-medium text-gray-800">{{ scope.row.stem }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120">
          <template #default="scope">
            <el-tag size="small" type="info">{{ scope.row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="question_type" label="题型" width="100">
          <template #default="scope">
            {{ scope.row.question_type === 'single' ? '单选题' : '填空题' }}
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度" width="150">
          <template #default="scope">
            <el-rate v-model="scope.row.difficulty" disabled :max="5" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="scope">
            <el-popconfirm title="确定删除这道题吗？" @confirm="deleteQuestion(scope.row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="p-4 flex justify-end border-t border-gray-100">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.size"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="total"
          @size-change="fetchQuestions"
          @current-change="fetchQuestions"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const categories = ref<string[]>([])
const tableData = ref([])
const total = ref(0)
const loading = ref(false)

const queryParams = ref({
  page: 1,
  size: 20,
  category: '',
  question_type: ''
})

const fetchCategories = async () => {
  try {
    const data = await request.get('/qbank/categories')
    categories.value = data as string[]
  } catch (e) {
    console.error(e)
  }
}

const fetchQuestions = async () => {
  loading.value = true
  try {
    const data: any = await request.post('/qbank/list', queryParams.value)
    tableData.value = data.items
    total.value = data.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const deleteQuestion = async (id: number) => {
  try {
    await request.delete(`/qbank/${id}`)
    ElMessage.success('删除成功')
    fetchQuestions()
  } catch (e) {
    // 拦截器已经弹出了详细错误
  }
}

const handleUploadSuccess = (response: any) => {
  ElMessage.success('题库文档上传成功，后台处理中...')
}

const handleUploadError = () => {
  ElMessage.error('题库文档上传失败')
}

onMounted(() => {
  fetchCategories()
  fetchQuestions()
})
</script>
