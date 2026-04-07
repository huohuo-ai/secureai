<template>
  <div class="compliance">
    <el-alert
      title="合规与审计"
      description="本页面提供满足监管要求的合规报告和审计追踪功能。"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    />
    
    <!-- 合规概览 -->
    <el-card shadow="hover" class="overview-card">
      <template #header>
        <div class="card-header">
          <span>合规概览 (最近30天)</span>
          <el-button type="primary" @click="exportData">
            <el-icon><Download /></el-icon>导出报告
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="20" class="compliance-stats">
        <el-col :span="6">
          <div class="compliance-item">
            <div class="compliance-value" :class="getComplianceClass(overview.summary?.gdpr_compliance_rate)">
              {{ overview.summary?.gdpr_compliance_rate?.toFixed(1) || 0 }}%
            </div>
            <div class="compliance-label">GDPR合规率</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="compliance-item">
            <div class="compliance-value" :class="getComplianceClass(overview.summary?.data_residency_compliance_rate)">
              {{ overview.summary?.data_residency_compliance_rate?.toFixed(1) || 0 }}%
            </div>
            <div class="compliance-label">数据驻留合规率</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="compliance-item">
            <div class="compliance-value warning">
              {{ overview.summary?.block_rate?.toFixed(2) || 0 }}%
            </div>
            <div class="compliance-label">请求阻断率</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="compliance-item">
            <div class="compliance-value">{{ overview.summary?.total_risk_events || 0 }}</div>
            <div class="compliance-label">风险事件数</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 风险分布 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>风险类型分布</span>
            </div>
          </template>
          <v-chart class="chart" :option="riskPieOption" autoresize />
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>敏感数据处理</span>
            </div>
          </template>
          <v-chart class="chart" :option="sensitivePieOption" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 审计追踪 -->
    <el-card shadow="hover" class="audit-trail-card">
      <template #header>
        <div class="card-header">
          <span>审计追踪记录</span>
          <div>
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              size="small"
              style="margin-right: 10px"
            />
            <el-button type="primary" size="small" @click="loadAuditTrail">查询</el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="auditTrail" stripe size="small" v-loading="loading">
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column prop="request_id" label="请求ID" width="180" show-overflow-tooltip />
        <el-table-column prop="user_id" label="用户" width="120" />
        <el-table-column prop="department" label="部门" width="100" />
        <el-table-column prop="resource" label="资源" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="input_tokens" label="Input" width="80" />
        <el-table-column prop="output_tokens" label="Output" width="80" />
        <el-table-column label="合规" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.compliance_flags?.gdpr_compliant" type="success" size="small">GDPR</el-tag>
            <el-tag v-else type="danger" size="small">GDPR</el-tag>
            <el-tag v-if="row.compliance_flags?.data_residency_compliant" type="success" size="small" style="margin-left: 4px">驻留</el-tag>
            <el-tag v-else type="danger" size="small" style="margin-left: 4px">驻留</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 合规规则 -->
    <el-card shadow="hover" class="rules-card">
      <template #header>
        <div class="card-header">
          <span>合规规则配置</span>
        </div>
      </template>
      
      <el-table :data="rules" stripe size="small">
        <el-table-column prop="name" label="规则名称" width="180" />
        <el-table-column prop="rule_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.rule_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="action" label="操作" width="100">
          <template #default="{ row }">
            <el-tag :type="getActionType(row.action)" size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="启用" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" disabled size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { getComplianceOverview, getAuditTrail, getComplianceRules, exportComplianceData } from '@/utils/api'
import dayjs from 'dayjs'

const overview = ref({
  summary: {},
  risk_distribution: {},
  sensitive_data_distribution: {}
})
const auditTrail = ref([])
const rules = ref([])
const loading = ref(false)
const dateRange = ref([])

const riskPieOption = computed(() => ({
  tooltip: {
    trigger: 'item'
  },
  legend: {
    orient: 'vertical',
    left: 'left'
  },
  series: [
    {
      type: 'pie',
      radius: '60%',
      data: Object.entries(overview.value.risk_distribution || {}).map(([key, value]) => ({
        name: getRiskTypeText(key),
        value
      })),
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }
  ]
}))

const sensitivePieOption = computed(() => ({
  tooltip: {
    trigger: 'item'
  },
  legend: {
    orient: 'vertical',
    left: 'left'
  },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      data: Object.entries(overview.value.sensitive_data_distribution || {}).map(([key, value]) => ({
        name: getSensitiveTypeText(key),
        value
      }))
    }
  ]
}))

const loadOverview = async () => {
  try {
    const res = await getComplianceOverview(30)
    overview.value = res.data
  } catch (error) {
    console.error('Failed to load compliance overview:', error)
  }
}

const loadAuditTrail = async () => {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0] + 'T00:00:00'
      params.end_date = dateRange.value[1] + 'T23:59:59'
    }
    const res = await getAuditTrail(params)
    auditTrail.value = res.data.records
  } catch (error) {
    console.error('Failed to load audit trail:', error)
  } finally {
    loading.value = false
  }
}

const loadRules = async () => {
  try {
    const res = await getComplianceRules()
    rules.value = res.data.items
  } catch (error) {
    console.error('Failed to load rules:', error)
  }
}

const exportData = async () => {
  try {
    const res = await exportComplianceData('json')
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `compliance_export_${dayjs().format('YYYYMMDD')}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export data:', error)
  }
}

const getComplianceClass = (rate) => {
  if (rate >= 95) return 'success'
  if (rate >= 80) return 'warning'
  return 'danger'
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

const getSensitiveTypeText = (type) => {
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

const getStatusType = (status) => {
  const map = { success: 'success', failure: 'danger', blocked: 'warning', timeout: 'info' }
  return map[status] || 'info'
}

const getActionType = (action) => {
  const map = { allow: 'success', block: 'danger', mask: 'warning', notify: 'info' }
  return map[action] || 'info'
}

onMounted(() => {
  loadOverview()
  loadAuditTrail()
  loadRules()
})
</script>

<style scoped>
.compliance {
  padding-bottom: 20px;
}

.overview-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.compliance-stats {
  text-align: center;
}

.compliance-item {
  padding: 20px;
}

.compliance-value {
  font-size: 36px;
  font-weight: 600;
  color: #303133;
}

.compliance-value.success {
  color: #67C23A;
}

.compliance-value.warning {
  color: #E6A23C;
}

.compliance-value.danger {
  color: #F56C6C;
}

.compliance-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.chart-row {
  margin-bottom: 20px;
}

.chart {
  height: 300px;
}

.audit-trail-card, .rules-card {
  margin-top: 20px;
}
</style>
