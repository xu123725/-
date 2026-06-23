<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-gray-800">错题本</h2>
    </div>

    <!-- 错题列表 -->
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
        <el-table-column prop="wrong_count" label="错误次数" width="100">
          <template #default="scope">
            <el-tag size="small" type="danger">{{ scope.row.wrong_count }} 次</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_wrong_at" label="最后错误时间" width="180">
          <template #default="scope">
            {{ new Date(scope.row.last_wrong_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-popconfirm title="确定移出错题本吗？" @confirm="removeWrongQuestion(scope.row.id)">
              <template #reference>
                <el-button link type="success" size="small">移出</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const tableData = ref([])
const loading = ref(false)

const fetchWrongQuestions = async () => {
  loading.value = true
  try {
    const data: any = await request.get('/wrongbook/list?limit=100&order_by=recent')
    tableData.value = data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const removeWrongQuestion = async (id: number) => {
  try {
    await request.delete(`/wrongbook/${id}`)
    ElMessage.success('已移出错题本')
    fetchWrongQuestions()
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchWrongQuestions()
})
</script>