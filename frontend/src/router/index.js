import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/',
    component: () => import('@/layouts/AuthLayout.vue'),
    meta: { guest: true },
    children: [
      { path: 'login', name: 'Login', component: () => import('@/views/auth/LoginView.vue') },
      { path: 'register', name: 'Register', component: () => import('@/views/auth/RegisterView.vue') },
    ],
  },
  {
    path: '/user',
    component: () => import('@/layouts/UserLayout.vue'),
    meta: { requiresAuth: true, role: 'user' },
    children: [
      { path: '', name: 'UserHome', component: () => import('@/views/user/HomeView.vue') },
      { path: 'bills', name: 'UserBills', component: () => import('@/views/user/BillsView.vue') },
      { path: 'bills/:id', name: 'UserBillDetail', component: () => import('@/views/user/BillDetailView.vue') },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      { path: '', name: 'AdminDashboard', component: () => import('@/views/admin/DashboardView.vue') },
      { path: 'piles/:id', name: 'AdminPileDetail', component: () => import('@/views/admin/PileDetailView.vue') },
      { path: 'reports', name: 'AdminReports', component: () => import('@/views/admin/ReportsView.vue') },
      { path: 'faults', name: 'AdminFaults', component: () => import('@/views/admin/FaultsView.vue') },
      { path: 'settings', name: 'AdminSettings', component: () => import('@/views/admin/SettingsView.vue') },
      { path: 'acceptance', name: 'AdminAcceptance', component: () => import('@/views/admin/AcceptanceView.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/** 路由守卫：鉴权与角色跳转 */
router.beforeEach((to) => {
  const { isLoggedIn, isAdmin } = useAuth()

  if (to.meta.requiresAuth && !isLoggedIn.value) {
    return '/login'
  }

  if (to.meta.guest && isLoggedIn.value) {
    return isAdmin.value ? '/admin' : '/user'
  }

  if (to.meta.role === 'admin' && isLoggedIn.value && !isAdmin.value) {
    return '/user'
  }

  if (to.meta.role === 'user' && isLoggedIn.value && isAdmin.value) {
    return '/admin'
  }

  return true
})

export default router
