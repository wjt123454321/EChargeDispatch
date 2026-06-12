<script setup>
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const { displayName, logout } = useAuth()

const navItems = [
  { path: '/admin', label: '桩监控', icon: '🔌' },
  { path: '/admin/reports', label: '统计报表', icon: '📊' },
  { path: '/admin/faults', label: '故障管理', icon: '⚠️' },
  { path: '/admin/settings', label: '系统配置', icon: '⚙️' },
  { path: '/admin/acceptance', label: '验收快照', icon: '📝' },
]

function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="sidebar__brand">
        <svg width="32" height="32" viewBox="0 0 40 40" fill="none">
          <rect width="40" height="40" rx="10" fill="var(--color-primary)"/>
          <path d="M14 12h4l6 14v-8h4l-8 16v-10h-4l2-12z" fill="#e8a838"/>
        </svg>
        <div>
          <span class="sidebar__title">ECharge</span>
          <span class="sidebar__role">管理端</span>
        </div>
      </div>
      <nav class="sidebar__nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="side-link"
          active-class="side-link--active"
        >
          <span class="side-link__icon">{{ item.icon }}</span>
          {{ item.label }}
        </router-link>
      </nav>
      <div class="sidebar__footer">
        <div class="admin-info">{{ displayName }}</div>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </aside>
    <main class="admin-main">
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--color-primary);
  color: #fff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  height: 100vh;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar__title {
  display: block;
  font-weight: 800;
  font-size: 1.0625rem;
}

.sidebar__role {
  font-size: 0.75rem;
  opacity: 0.6;
}

.sidebar__nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.side-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  font-size: 0.875rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  border-radius: var(--radius-md);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.side-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.side-link--active {
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
}

.side-link__icon {
  font-size: 1rem;
  width: 22px;
  text-align: center;
}

.sidebar__footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.admin-info {
  font-size: 0.8125rem;
  opacity: 0.7;
  margin-bottom: 8px;
}

.logout-btn {
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.6);
  transition: color var(--transition-fast);
}

.logout-btn:hover {
  color: #fff;
}

.admin-main {
  flex: 1;
  background: var(--color-bg);
  overflow-y: auto;
}

@media (max-width: 768px) {
  .sidebar {
    width: 64px;
  }

  .sidebar__brand div,
  .sidebar__role,
  .side-link span:not(.side-link__icon),
  .admin-info,
  .logout-btn {
    display: none;
  }

  .sidebar__brand {
    justify-content: center;
    padding: 16px 8px;
  }

  .side-link {
    justify-content: center;
    padding: 12px 8px;
  }
}
</style>
