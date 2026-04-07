<template>
  <div class="risk-events">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-statistic title="今日风险事件" :value="todayRisks" value-style="color: #F56C6C" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="高风险事件" :value="highRisks" value-style="color: #E6A23C" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="已阻断请求" :value="blockedRequests" value-style="color: #67C23A" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="平均风险评分" :value="avgRiskScore" :precision="2" />
      </el-col>
    </el-row>
    
    <el-card shadow="hover" class="risk-table-card">
      <template #header>
        <div class="card-header">
          <span>风险事件列表</span>
          <div class="header-actions">
            <el-radio-group v-model="filterRiskLevel" size="small" @change="handleFilterChange">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="critical">严重</el-radio-button>
              <el-radio-button label="high">高</el-radio-button>
              <el-radio-button label="medium">中</el-radio-button>
              <el-radio-button label="low">低</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
      
      <el-table :data="riskEvents" v-loading="loading" stripe>
        <el-table-column prop="created_at" label="检测时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="risk_type" label="风险类型" width="150">
          <template #default="{ row }">
            <el-tag :type="getRiskTypeStyle(row.risk_type)" size="small">
              {{ getRiskTypeText(row.risk_type) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskLevelType(row.risk_level)" effect="dark" size="small">
              {{ getRiskLevelText(row.risk_level) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="detection_rule" label="检测规则" width="150" />
        
        <el-table-column prop="detected_content" label="检测到内容" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="detected-content">{{ row.detected_content }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="confidence_score" label="置信度" width="100">
          <template #default="{ row }">
            <el-progress 
              :percentage="Math.round(row.confidence_score * 100)" 
              :color="getConfidenceColor(row.confidence_score)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        
        <el-table-column prop="action_taken" label="处理操作" width="100">
          <template #default="{ row }">
            <el-tag :type="getActionType(row.action_taken)" size="small">
              {{ getActionText(row.action_taken) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="blocked" label="是否阻断" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.blocked" type="danger" size="small">已阻断</el-tag>
            <el-tag v-else type="info" size="small">通过</el-tag>
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
import { getRiskEvents } from '@/utils/api'
import dayjs from 'dayjs'

const router = useRouter()
const loading = ref(false)
const riskEvents = ref([])
const filterRiskLevel = ref('')

const todayRisks = ref(0)
const highRisks = ref(0)
const blockedRequests = ref(0)
const avgRiskScore = ref(0)

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
    
    if (filterRiskLevel.value) {
      params.risk_level = filterRiskLevel.value
    }
    
    const res = await getRiskEvents(params)
    riskEvents.value = res.data.items
    pagination.total = res.data.total
    
    // 计算统计
    calculateStats()
  } catch (error) {
    console.error('Failed to load risk events:', error)
  } finally {
    loading.value = false
  }
}

const calculateStats = () => {
  // 这里简化处理，实际应该从API获取
  todayRisks.value = riskEvents.value.filter(r => 
    dayjs(r.created_at).isAfter(dayjs().startOf('day'))
  ).length
  
  highRisks.value = riskEvents.value.filter(r => 
    r.risk_level === 'high' || r.risk_level === 'critical'
  ).length
  
  blockedRequests.value = riskEvents.value.filter(r => r.blocked).length
  
  const avg = riskEvents.value.reduce((sum, r) => sum + r.confidence_score, 0) / riskEvents.value.length
  avgRiskScore.value = avg || 0
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

const getRiskTypeStyle = (type) => {
  const map = {
    sensitive_data: 'danger',
    prompt_injection: 'warning',
    jailbreak: 'danger',
    data_exfiltration: 'danger',
    policy_violation: 'warning',
    anomaly: 'info',
    cost_spike: 'info'
  }
  return map[type] || 'info'
}

const getRiskTypeText = (type) => {
  const map = {
    sensitive_data: '敏感数据',
    prompt_injection: 'Prompt注入',
    jailbreak: '越狱攻击',
    data_exfiltration: '数据外泄',
    policy_violation: '策略违规',
    anomaly: '异常行为',
    cost_spike: '成本飙升'
  }
  return map[type] || type
}

const getRiskLevelType = (level) => {
  const map = { low: 'info', medium: 'warning', high: 'danger', critical: 'danger' }
  return map[level] || 'info'
}

const getRiskLevelText = (level) => {
  const map = { low: '低', medium: '中', high: '高', critical: '严重' }
  return map[level] || level
}

const getConfidenceColor = (score) => {
  if (score >= 0.9) return '#F56C6C'
  if (score >= 0.7) return '#E6A23C'
  return '#67C23A'
}

const getActionType = (action) => {
  const map = { log: 'info', warn: 'warning', block: 'danger', mask: 'success', notify: 'primary' }
  return map[action] || 'info'
}

const getActionText = (action) => {
  const map = { log: '记录', warn: '警告', block: '阻断', mask: '脱敏', notify: '通知' }
  return map[action] || action
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.risk-events {
  padding-bottom: 20px;
}

.stat-row {
  margin-bottom: 20px;
}

.stat-row :deep(.el-statistic__content) {
  font-size: 28px;
  font-weight: 600;
}

.risk-table-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detected-content {
  color: #606266;
  font-size: 13px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
