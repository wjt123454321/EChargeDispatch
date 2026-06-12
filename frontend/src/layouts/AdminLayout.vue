<script setup>
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const { displayName, logout } = useAuth()

const navItems = [
  { path: '/admin', label: '桩监控', icon: '🔌' },
  { path: '/admin/reports', label: '报表', icon: '📊' },
  { path: '/admin/faults', label: '故障', icon: '⚠️' },
  { path: '/admin/settings', label: '配置', icon: '⚙️' },
  { path: '/admin/acceptance', label: '验收', icon: '📝' },
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
          <rect width="40" height="40" rx="10" fill="rgba(255,255,255,0.15)"/>
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
        <button class="logout-btn" type="button" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <div class="admin-shell">
      <header class="mobile-header">
        <span class="mobile-header__title">ECharge 管理端</span>
        <button class="mobile-header__logout" type="button" @click="handleLogout">退出</button>
      </header>

      <main class="admin-main">
        <router-view v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </router-view>
      </main>

      <nav class="bottom-nav" aria-label="管理端导航">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="bottom-nav__item"
          active-class="bottom-nav__item--active"
        >
          <span class="bottom-nav__icon">{{ item.icon }}</span>
          <span class="bottom-nav__label">{{ item.label }}</span>
        </router-link>
      </nav>
    </div>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
  min-height: 100dvh;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--color-primary);
  color: #fff;
  display: none;
  flex-direction: column;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  height: 100vh;
  height: 100dvh;
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

.sidebar .logout-btn {
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.6);
  transition: color var(--transition-fast);
}

.sidebar .logout-btn:hover {
  color: #fff;
}

.admin-shell {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--color-bg);
}

.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  padding: 0 16px;
  padding-top: env(safe-area-inset-top, 0px);
  background: var(--color-primary);
  color: #fff;
  position: sticky;
  top: 0;
  z-index: 100;
}

.mobile-header__title {
  font-weight: 800;
  font-size: 1rem;
}

.mobile-header__logout {
  font-size: 0.8125rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
}

.mobile-header__logout:active {
  background: rgba(255, 255, 255, 0.12);
}

.admin-main {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

.bottom-nav {
  display: flex;
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  height: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px));
  padding-bottom: env(safe-area-inset-bottom, 0px);
  background: var(--color-bg-elevated);
  border-top: 1px solid var(--color-border-light);
  box-shadow: 0 -2px 12px rgba(28, 27, 25, 0.06);
}

.bottom-nav__item {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  text-decoration: none;
  color: var(--color-text-muted);
  font-size: 0.625rem;
  font-weight: 600;
  transition: color var(--transition-fast);
  padding: 0 2px;
}

.bottom-nav__item--active {
  color: var(--color-primary);
}

.bottom-nav__icon {
  font-size: 1.0625rem;
  line-height: 1;
}

.bottom-nav__label {
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

@media (min-width: 769px) {
  .sidebar {
    display: flex;
  }

  .mobile-header,
  .bottom-nav {
    display: none;
  }

  .admin-main :deep(.page) {
    padding-bottom: 32px;
  }
}
</style>
