<template>
  <div class="audit-logs">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <div class="header-actions">
            <el-button type="primary" :icon="Refresh" @click="loadData" :loading="loading">
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 搜索过滤 -->
      <el-form :model="searchForm" inline class="search-form">
        <el-form-item label="用户ID">
          <el-input v-model="searchForm.user_id" placeholder="输入用户ID" clearable />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="searchForm.department" placeholder="选择部门" clearable>
            <el-option v-for="dept in departments" :key="dept" :label="dept" :value="dept" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable>
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failure" />
            <el-option label="已阻断" value="blocked" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
      
      <!-- 数据表格 -->
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <h4>输入预览</h4>
              <p class="content-text">{{ row.input_preview }}</p>
              <h4>输出预览</h4>
              <p class="content-text">{{ row.output_preview || '-' }}</p>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="request_id" label="请求ID" width="180" show-overflow-tooltip />
        <el-table-column prop="user_id" label="用户" width="120" />
        <el-table-column prop="department" label="部门" width="100" />
        <el-table-column prop="project" label="项目" width="120" />
        <el-table-column prop="provider" label="提供商" width="100" />
        <el-table-column prop="model" label="模型" width="150" />
        
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="Token使用" width="180">
          <template #default="{ row }">
            <div class="token-info">
              <span class="token-input">In: {{ row.input_tokens }}</span>
              <span class="token-output">Out: {{ row.output_tokens }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="estimated_cost" label="成本" width="100">
          <template #default="{ row }">
            <span class="cost">${{ row.estimated_cost?.toFixed(4) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="latency_ms" label="延迟" width="100">
          <template #default="{ row }">
            {{ row.latency_ms }}ms
          </template>
        </el-table-column>
        
        <el-table-column prop="request_time" label="请求时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.request_time) }}
          </template>
        </el-table-column>
        
        <el-table-column label="风险" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.risk_count > 0" type="danger" size="small">
              {{ row.risk_count }}个
            </el-tag>
            <span v-else class="no-risk">-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="审计日志详情" width="800px">
      <el-descriptions :column="2" border v-if="currentLog">
        <el-descriptions-item label="请求ID">{{ currentLog.request_id }}</el-descriptions-item>
        <el-descriptions-item label="用户">{{ currentLog.user_id }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ currentLog.department }}</el-descriptions-item>
        <el-descriptions-item label="项目">{{ currentLog.project }}</el-descriptions-item>
        <el-descriptions-item label="提供商">{{ currentLog.provider }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ currentLog.model }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentLog.status)">
            {{ getStatusText(currentLog.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="延迟">{{ currentLog.latency_ms }}ms</el-descriptions-item>
        <el-descriptions-item label="Input Tokens">{{ currentLog.input_tokens }}</el-descriptions-item>
        <el-descriptions-item label="Output Tokens">{{ currentLog.output_tokens }}</el-descriptions-item>
        <el-descriptions-item label="预估成本">${{ currentLog.estimated_cost }}</el-descriptions-item>
        <el-descriptions-item label="客户端IP">{{ currentLog.client_ip }}</el-descriptions-item>
        <el-descriptions-item label="请求时间">{{ formatDate(currentLog.request_time) }}</el-descriptions-item>
        <el-descriptions-item label="响应时间">{{ formatDate(currentLog.response_time) }}</el-descriptions-item>
        <el-descriptions-item label="GDPR合规">
          <el-tag :type="currentLog.gdpr_compliant ? 'success' : 'danger'">
            {{ currentLog.gdpr_compliant ? '合规' : '不合规' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="数据驻留合规">
          <el-tag :type="currentLog.data_residency_compliant ? 'success' : 'danger'">
            {{ currentLog.data_residency_compliant ? '合规' : '不合规' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
      
      <div class="detail-section" v-if="currentLog?.risk_detections?.length">
        <h4>风险检测</h4>
        <el-table :data="currentLog.risk_detections" size="small">
          <el-table-column prop="risk_type" label="风险类型" />
          <el-table-column prop="risk_level" label="等级">
            <template #default="{ row }">
              <el-tag :type="getRiskLevelType(row.risk_level)" size="small">
                {{ row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detection_rule" label="规则" />
          <el-table-column prop="action_taken" label="操作" />
        </el-table>
      </div>
      
      <div class="detail-section" v-if="currentLog?.sensitive_data_hits?.length">
        <h4>敏感数据命中</h4>
        <el-table :data="currentLog.sensitive_data_hits" size="small">
          <el-table-column prop="data_type" label="数据类型" />
          <el-table-column prop="detection_method" label="检测方法" />
          <el-table-column prop="masked_content" label="脱敏内容" show-overflow-tooltip />
          <el-table-column prop="position" label="位置" />
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getAuditLogs, getAuditLogDetail } from '@/utils/api'
import dayjs from 'dayjs'

const loading = ref(false)
const logs = ref([])
const detailVisible = ref(false)
const currentLog = ref(null)

const departments = ['研发部', '产品部', '市场部', '销售部', '运营部', '法务部', '人事部', '财务部']

const searchForm = reactive({
  user_id: '',
  department: '',
  status: '',
  dateRange: []
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      user_id: searchForm.user_id || undefined,
      department: searchForm.department || undefined,
      status: searchForm.status || undefined
    }
    
    if (searchForm.dateRange?.length === 2) {
      params.start_date = searchForm.dateRange[0] + 'T00:00:00'
      params.end_date = searchForm.dateRange[1] + 'T23:59:59'
    }
    
    const res = await getAuditLogs(params)
    logs.value = res.data.items
    pagination.total = res.data.total
  } catch (error) {
    console.error('Failed to load audit logs:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

const resetSearch = () => {
  searchForm.user_id = ''
  searchForm.department = ''
  searchForm.status = ''
  searchForm.dateRange = []
  handleSearch()
}

const handlePageChange = (page) => {
  pagination.page = page
  loadData()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.page = 1
  loadData()
}

const viewDetail = async (row) => {
  try {
    const res = await getAuditLogDetail(row.id)
    currentLog.value = res.data
    detailVisible.value = true
  } catch (error) {
    console.error('Failed to load log detail:', error)
  }
}

const getStatusType = (status) => {
  const map = { success: 'success', failure: 'danger', blocked: 'warning', timeout: 'info' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { success: '成功', failure: '失败', blocked: '已阻断', timeout: '超时' }
  return map[status] || status
}

const getRiskLevelType = (level) => {
  const map = { low: 'info', medium: 'warning', high: 'danger', critical: 'danger' }
  return map[level] || 'info'
}

const formatDate = (date) => {
  return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.audit-logs {
  padding-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.token-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.token-input {
  color: #409EFF;
}

.token-output {
  color: #67C23A;
}

.cost {
  color: #E6A23C;
  font-weight: 500;
}

.no-risk {
  color: #c0c4cc;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.expand-content {
  padding: 20px;
  background: #f5f7fa;
}

.expand-content h4 {
  margin: 16px 0 8px;
  color: #606266;
  font-size: 14px;
}

.expand-content h4:first-child {
  margin-top: 0;
}

.content-text {
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  background: #fff;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}

.detail-section {
  margin-top: 24px;
}

.detail-section h4 {
  margin-bottom: 12px;
  color: #303133;
  font-size: 16px;
  border-left: 4px solid #409EFF;
  padding-left: 12px;
}
</style>
