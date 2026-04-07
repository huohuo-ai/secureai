import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表板', icon: 'Odometer' }
      },
      {
        path: 'audit-logs',
        name: 'AuditLogs',
        component: () => import('@/views/AuditLogs.vue'),
        meta: { title: '审计日志', icon: 'Document' }
      },
      {
        path: 'risk-events',
        name: 'RiskEvents',
        component: () => import('@/views/RiskEvents.vue'),
        meta: { title: '风险事件', icon: 'Warning' }
      },
      {
        path: 'sensitive-data',
        name: 'SensitiveData',
        component: () => import('@/views/SensitiveData.vue'),
        meta: { title: '敏感数据', icon: 'Lock' }
      },
      {
        path: 'cost-control',
        name: 'CostControl',
        component: () => import('@/views/CostControl.vue'),
        meta: { title: '成本管控', icon: 'Money' }
      },
      {
        path: 'compliance',
        name: 'Compliance',
        component: () => import('@/views/Compliance.vue'),
        meta: { title: '合规报告', icon: 'DocumentChecked' }
      },
      {
        path: 'api-test',
        name: 'ApiTest',
        component: () => import('@/views/ApiTest.vue'),
        meta: { title: 'API测试', icon: 'Promotion' }
      },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
