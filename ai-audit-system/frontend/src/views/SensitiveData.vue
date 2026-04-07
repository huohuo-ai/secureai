<template>
  <div class="sensitive-data">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-title">敏感数据命中总数</div>
            <div class="stat-value" style="color: #F56C6C">{{ totalHits.toLocaleString() }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-title">身份证检测</div>
            <div class="stat-value" style="color: #E6A23C">{{ idCardHits.toLocaleString() }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-title">手机号检测</div>
            <div class="stat-value" style="color: #409EFF">{{ phoneHits.toLocaleString() }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-card shadow="hover" class="data-table-card">
      <template #header>
        <div class="card-header">
          <span>敏感数据检测记录</span>
          <el-select v-model="filterType" placeholder="数据类型" clearable @change="handleFilterChange">
            <el-option label="身份证" value="id_card" />
            <el-option label="手机号" value="phone" />
            <el-option label="银行卡" value="bank_card" />
            <el-option label="邮箱" value="email" />
            <el-option label="IP地址" value="ip_address" />
            <el-option label="API密钥" value="api_key" />
          </el-select>
        </div>
      </template>
      
      <el-alert
        title="安全提示"
        description="以下展示的内容已自动脱敏处理，实际完整内容仅在加密日志中存储。"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 20px"
      />
      
      <el-table :data="sensitiveHits" v-loading="loading" stripe>
        <el-table-column prop="created_at" label="检测时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="data_type" label="数据类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getDataTypeStyle(row.data_type)" size="small">
              {{ getDataTypeText(row.data_type) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="detection_method" label="检测方法" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.detection_method }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="matched_pattern" label="匹配规则" width="150" />
        
        <el-table-column prop="masked_content" label="脱敏内容">
          <template #default="{ row }">
            <code class="masked-content">{{ row.masked_content }}</code>
          </template>
        </el-table-column>
        
        <el-table-column prop="position" label="位置" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.position === 'input'" size="small" type="primary">输入</el-tag>
            <el-tag v-else size="small" type="success">输出</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewAuditLog(row.audit_log_id)">
              查看日志
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSensitiveDataHits, getAuditStats } from '@/utils/api'
import dayjs from 'dayjs'

const router = useRouter()
const loading = ref(false)
const sensitiveHits = ref([])
const filterType = ref('')

const totalHits = ref(0)
const idCardHits = ref(0)
const phoneHits = ref(0)

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
      limit: pagination.pageSize
    }
    
    if (filterType.value) {
      params.data_type = filterType.value
    }
    
    const res = await getSensitiveDataHits(params)
    sensitiveHits.value = res.data.items
    pagination.total = res.data.total
  } catch (error) {
    console.error('Failed to load sensitive data hits:', error)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await getAuditStats(30)
    const distribution = res.data.sensitive_data_distribution || {}
    
    totalHits.value = Object.values(distribution).reduce((a, b) => a + b, 0)
    idCardHits.value = distribution.id_card || 0
    phoneHits.value = distribution.phone || 0
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

const handleFilterChange = () => {
  pagination.page = 1
  loadData()
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

const viewAuditLog = (auditLogId) => {
  router.push(`/audit-logs?id=${auditLogId}`)
}

const getDataTypeStyle = (type) => {
  const map = {
    id_card: 'danger',
    phone: 'warning',
    bank_card: 'danger',
    email: 'primary',
    ip_address: 'info',
    source_code: 'warning',
    api_key: 'danger',
    password: 'danger',
    business_secret: 'warning',
    personal_info: 'info'
  }
  return map[type] || 'info'
}

const getDataTypeText = (type) => {
  const map = {
    id_card: '身份证',
    phone: '手机号',
    bank_card: '银行卡',
    email: '邮箱',
    ip_address: 'IP地址',
    source_code: '源代码',
    api_key: 'API密钥',
    password: '密码',
    business_secret: '商业机密',
    personal_info: '个人信息'
  }
  return map[type] || type
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadData()
  loadStats()
})
</script>

<style scoped>
.sensitive-data {
  padding-bottom: 20px;
}

.stat-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 20px;
}

.stat-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
}

.data-table-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.masked-content {
  background: #f5f7fa;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
  color: #606266;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
