<template>
  <div class="cost-control">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-title">今日成本</div>
            <div class="stat-value" style="color: #67C23A">${{ dashboard.today?.cost?.toFixed(2) || '0.00' }}</div>
            <div class="stat-subtitle">{{ dashboard.today?.requests || 0 }} 次请求</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-title">本月成本</div>
            <div class="stat-value" style="color: #409EFF">${{ dashboard.this_month?.cost?.toFixed(2) || '0.00' }}</div>
            <div class="stat-subtitle">{{ dashboard.this_month?.requests || 0 }} 次请求</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-title">本月Token数</div>
            <div class="stat-value" style="color: #E6A23C">{{ (dashboard.this_month?.tokens || 0).toLocaleString() }}</div>
            <div class="stat-subtitle">Input + Output</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-title">预算告警</div>
            <div class="stat-value" style="color: #F56C6C">{{ dashboard.alerts?.length || 0 }}</div>
            <div class="stat-subtitle">个用户超出90%预算</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 部门成本分布 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>部门成本分布</span>
            </div>
          </template>
          <v-chart class="chart" :option="deptChartOption" autoresize />
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>预算告警列表</span>
            </div>
          </template>
          <el-table :data="dashboard.alerts" stripe size="small">
            <el-table-column prop="user_id" label="用户" />
            <el-table-column prop="department" label="部门" />
            <el-table-column label="预算使用" width="200">
              <template #default="{ row }">
                <el-progress 
                  :percentage="Math.round(row.percentage)" 
                  :color="getAlertColor(row.percentage)"
                />
                <div class="budget-text">
                  ${{ row.cost_used?.toFixed(2) }} / ${{ row.cost_budget }}
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 用户配额管理 -->
    <el-card shadow="hover" class="quota-card">
      <template #header>
        <div class="card-header">
          <span>用户配额管理</span>
          <el-button type="primary" @click="loadQuotas">刷新</el-button>
        </div>
      </template>
      
      <el-table :data="quotas" v-loading="quotaLoading" stripe>
        <el-table-column prop="user_id" label="用户ID" width="120" />
        <el-table-column prop="department" label="部门" width="100" />
        
        <el-table-column label="日限额使用" width="200">
          <template #default="{ row }">
            <el-progress 
              :percentage="Math.min(100, Math.round(row.daily_used / row.daily_limit * 100))"
              :status="row.daily_used > row.daily_limit ? 'exception' : ''"
            />
            <div class="quota-text">{{ row.daily_used.toLocaleString() }} / {{ row.daily_limit.toLocaleString() }}</div>
          </template>
        </el-table-column>
        
        <el-table-column label="月限额使用" width="200">
          <template #default="{ row }">
            <el-progress 
              :percentage="Math.min(100, Math.round(row.monthly_used / row.monthly_limit * 100))"
            />
            <div class="quota-text">{{ row.monthly_used.toLocaleString() }} / {{ row.monthly_limit.toLocaleString() }}</div>
          </template>
        </el-table-column>
        
        <el-table-column label="预算使用" width="200">
          <template #default="{ row }">
            <el-progress 
              :percentage="Math.min(100, Math.round(row.cost_used / row.cost_budget * 100))"
              :color="getBudgetColor(row.cost_used, row.cost_budget)"
            />
            <div class="quota-text">${{ row.cost_used?.toFixed(2) }} / ${{ row.cost_budget }}</div>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" link @click="editQuota(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑配额对话框 -->
    <el-dialog v-model="quotaDialogVisible" title="编辑用户配额" width="500px">
      <el-form :model="quotaForm" label-width="120px">
        <el-form-item label="用户ID">
          <span>{{ quotaForm.user_id }}</span>
        </el-form-item>
        <el-form-item label="日Token限额">
          <el-input-number v-model="quotaForm.daily_limit" :min="1000" :step="10000" />
        </el-form-item>
        <el-form-item label="月Token限额">
          <el-input-number v-model="quotaForm.monthly_limit" :min="10000" :step="100000" />
        </el-form-item>
        <el-form-item label="预算($)">
          <el-input-number v-model="quotaForm.cost_budget" :min="10" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quotaDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveQuota">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getCostDashboard, getUserQuotas, updateUserQuota } from '@/utils/api'
import { ElMessage } from 'element-plus'

const dashboard = ref({
  today: {},
  this_month: {},
  department_breakdown: [],
  alerts: []
})
const quotas = ref([])
const quotaLoading = ref(false)
const quotaDialogVisible = ref(false)
const quotaForm = reactive({
  user_id: '',
  daily_limit: 100000,
  monthly_limit: 2000000,
  cost_budget: 1000
})

const deptChartOption = computed(() => ({
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
    data: dashboard.value.department_breakdown?.map(d => d.department) || []
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      formatter: '${value}'
    }
  },
  series: [
    {
      type: 'bar',
      data: dashboard.value.department_breakdown?.map(d => d.cost) || [],
      itemStyle: {
        color: '#409EFF'
      }
    }
  ]
}))

const loadDashboard = async () => {
  try {
    const res = await getCostDashboard()
    dashboard.value = res.data
  } catch (error) {
    console.error('Failed to load dashboard:', error)
  }
}

const loadQuotas = async () => {
  quotaLoading.value = true
  try {
    const res = await getUserQuotas({ limit: 50 })
    quotas.value = res.data.items
  } catch (error) {
    console.error('Failed to load quotas:', error)
  } finally {
    quotaLoading.value = false
  }
}

const editQuota = (row) => {
  quotaForm.user_id = row.user_id
  quotaForm.daily_limit = row.daily_limit
  quotaForm.monthly_limit = row.monthly_limit
  quotaForm.cost_budget = row.cost_budget
  quotaDialogVisible.value = true
}

const saveQuota = async () => {
  try {
    await updateUserQuota(quotaForm.user_id, {
      daily_limit: quotaForm.daily_limit,
      monthly_limit: quotaForm.monthly_limit,
      cost_budget: quotaForm.cost_budget
    })
    ElMessage.success('配额更新成功')
    quotaDialogVisible.value = false
    loadQuotas()
  } catch (error) {
    ElMessage.error('配额更新失败')
  }
}

const getAlertColor = (percentage) => {
  if (percentage >= 100) return '#F56C6C'
  if (percentage >= 90) return '#E6A23C'
  return '#67C23A'
}

const getBudgetColor = (used, budget) => {
  const pct = used / budget
  if (pct >= 0.9) return '#F56C6C'
  if (pct >= 0.7) return '#E6A23C'
  return '#67C23A'
}

onMounted(() => {
  loadDashboard()
  loadQuotas()
})
</script>

<style scoped>
.cost-control {
  padding-bottom: 20px;
}

.stat-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 10px;
}

.stat-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
}

.stat-subtitle {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.chart-row {
  margin-bottom: 20px;
}

.chart {
  height: 300px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.budget-text {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  text-align: center;
}

.quota-card {
  margin-top: 20px;
}

.quota-text {
  font-size: 12px;
  color: #606266;
  margin-top: 4px;
}
</style>
