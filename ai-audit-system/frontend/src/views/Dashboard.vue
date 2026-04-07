<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon blue">
              <el-icon size="32"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_requests?.toLocaleString() || 0 }}</div>
              <div class="stat-label">总请求数 (30天)</div>
              <div class="stat-change positive">
                <el-icon><ArrowUp /></el-icon> +12.5%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon green">
              <el-icon size="32"><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">${{ stats.total_cost?.toFixed(2) || '0.00' }}</div>
              <div class="stat-label">总成本 (30天)</div>
              <div class="stat-change positive">
                <el-icon><ArrowUp /></el-icon> +8.3%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon orange">
              <el-icon size="32"><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalRisks?.toLocaleString() || 0 }}</div>
              <div class="stat-label">风险事件 (30天)</div>
              <div class="stat-change negative">
                <el-icon><ArrowDown /></el-icon> -5.2%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon red">
              <el-icon size="32"><Lock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalSensitive?.toLocaleString() || 0 }}</div>
              <div class="stat-label">敏感数据命中 (30天)</div>
              <div class="stat-change negative">
                <el-icon><ArrowUp /></el-icon> +3.1%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>请求趋势 (30天)</span>
              <el-radio-group v-model="trendType" size="small">
                <el-radio-button label="requests">请求数</el-radio-button>
                <el-radio-button label="tokens">Token数</el-radio-button>
                <el-radio-button label="cost">成本</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart class="trend-chart" :option="trendChartOption" autoresize />
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>状态分布</span>
            </div>
          </template>
          <v-chart class="pie-chart" :option="statusPieOption" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 风险分析 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>风险类型分布</span>
            </div>
          </template>
          <v-chart class="bar-chart" :option="riskBarOption" autoresize />
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>敏感数据类型</span>
            </div>
          </template>
          <v-chart class="bar-chart" :option="sensitiveBarOption" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近的审计日志 -->
    <el-card class="recent-logs" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>最近的审计日志</span>
          <el-button type="primary" link @click="$router.push('/audit-logs')">
            查看全部
          </el-button>
        </div>
      </template>
      
      <el-table :data="recentLogs" stripe>
        <el-table-column prop="request_id" label="请求ID" width="180" show-overflow-tooltip />
        <el-table-column prop="user_id" label="用户" width="120" />
        <el-table-column prop="department" label="部门" width="100" />
        <el-table-column prop="model" label="模型" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="input_tokens" label="Input Tokens" width="120" />
        <el-table-column prop="output_tokens" label="Output Tokens" width="120" />
        <el-table-column prop="estimated_cost" label="成本" width="100">
          <template #default="{ row }">
            ${{ row.estimated_cost?.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="request_time" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.request_time) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { use } from 'echarts/core'
import { getAuditStats, getDailyStats, getAuditLogs } from '@/utils/api'
import dayjs from 'dayjs'

const stats = ref({})
const dailyStats = ref([])
const recentLogs = ref([])
const trendType = ref('requests')
const totalRisks = ref(0)
const totalSensitive = ref(0)

const trendChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: dailyStats.value.map(d => dayjs(d.date).format('MM-DD')),
    boundaryGap: false
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      name: trendType.value === 'requests' ? '请求数' : trendType.value === 'tokens' ? 'Token数' : '成本($)',
      type: 'line',
      smooth: true,
      data: dailyStats.value.map(d => 
        trendType.value === 'requests' ? d.requests : 
        trendType.value === 'tokens' ? d.input_tokens + d.output_tokens : 
        d.cost
      ),
      areaStyle: {
        opacity: 0.3
      },
      itemStyle: {
        color: '#409EFF'
      }
    }
  ]
}))

const statusPieOption = computed(() => ({
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
      label: {
        show: false
      },
      data: Object.entries(stats.value.status_distribution || {}).map(([key, value]) => ({
        name: getStatusText(key),
        value
      }))
    }
  ]
}))

const riskBarOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: Object.keys(stats.value.risk_distribution || {}).map(k => getRiskTypeText(k)),
    axisLabel: { rotate: 30 }
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      type: 'bar',
      data: Object.values(stats.value.risk_distribution || {}),
      itemStyle: {
        color: '#E6A23C'
      }
    }
  ]
}))

const sensitiveBarOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' }
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: Object.keys(stats.value.sensitive_data_distribution || {}).map(k => getSensitiveTypeText(k)),
    axisLabel: { rotate: 30 }
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      type: 'bar',
      data: Object.values(stats.value.sensitive_data_distribution || {}),
      itemStyle: {
        color: '#F56C6C'
      }
    }
  ]
}))

const getStatusType = (status) => {
  const map = {
    success: 'success',
    failure: 'danger',
    blocked: 'warning',
    timeout: 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    success: '成功',
    failure: '失败',
    blocked: '已阻断',
    timeout: '超时'
  }
  return map[status] || status
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

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const loadData = async () => {
  try {
    // 加载统计数据
    const statsRes = await getAuditStats(30)
    stats.value = statsRes.data
    
    // 计算风险总数
    totalRisks.value = Object.values(statsRes.data.risk_distribution || {}).reduce((a, b) => a + b, 0)
    totalSensitive.value = Object.values(statsRes.data.sensitive_data_distribution || {}).reduce((a, b) => a + b, 0)
    
    // 加载每日统计
    const dailyRes = await getDailyStats(30)
    dailyStats.value = dailyRes.data
    
    // 加载最近日志
    const logsRes = await getAuditLogs({ limit: 10 })
    recentLogs.value = logsRes.data.items
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  padding-bottom: 20px;
}

.stat-cards {
  margin-bottom: 20px;
}

.stat-card {
  height: 140px;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100px;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
}

.stat-icon.blue {
  background: rgba(64, 158, 255, 0.1);
  color: #409EFF;
}

.stat-icon.green {
  background: rgba(103, 194, 58, 0.1);
  color: #67C23A;
}

.stat-icon.orange {
  background: rgba(230, 162, 60, 0.1);
  color: #E6A23C;
}

.stat-icon.red {
  background: rgba(245, 108, 108, 0.1);
  color: #F56C6C;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.stat-change {
  font-size: 13px;
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-change.positive {
  color: #67C23A;
}

.stat-change.negative {
  color: #F56C6C;
}

.chart-row {
  margin-bottom: 20px;
}

.chart-card {
  height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trend-chart {
  height: 320px;
}

.pie-chart {
  height: 320px;
}

.bar-chart {
  height: 320px;
}

.recent-logs {
  margin-top: 20px;
}
</style>
