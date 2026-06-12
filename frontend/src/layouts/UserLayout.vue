<script setup>
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const { displayName, logout } = useAuth()

const navItems = [
  { path: '/user', label: '充电服务', icon: '⚡' },
  { path: '/user/bills', label: '我的账单', icon: '📋' },
]

function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-layout">
    <header class="header">
      <div class="header__left">
        <router-link to="/user" class="header__logo">
          <svg width="28" height="28" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="10" fill="var(--color-primary)"/>
            <path d="M14 12h4l6 14v-8h4l-8 16v-10h-4l2-12z" fill="#e8a838"/>
          </svg>
          <span>ECharge</span>
        </router-link>
        <nav class="header__nav">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-link"
            active-class="nav-link--active"
          >
            <span class="nav-link__icon">{{ item.icon }}</span>
            {{ item.label }}
          </router-link>
        </nav>
      </div>
      <div class="header__right">
        <span class="user-badge">{{ displayName }}</span>
        <button class="logout-btn" @click="handleLogout">退出</button>
      </div>
    </header>
    <main class="main">
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  height: var(--header-height);
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header__left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.header__logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 1.0625rem;
  color: var(--color-text);
  text-decoration: none;
}

.header__nav {
  display: flex;
  gap: 4px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--color-text);
  background: var(--color-surface-muted);
}

.nav-link--active {
  color: var(--color-primary);
  background: var(--color-primary-muted);
}

.nav-link__icon {
  font-size: 0.9375rem;
}

.header__right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-badge {
  font-size: 0.8125rem;
  font-weight: 600;
  padding: 6px 14px;
  background: var(--color-surface-muted);
  border-radius: 100px;
  color: var(--color-text-secondary);
}

.logout-btn {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-muted);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.logout-btn:hover {
  color: var(--color-danger);
  background: rgba(184, 58, 58, 0.08);
}

.main {
  flex: 1;
}

@media (max-width: 640px) {
  .header__nav {
    display: none;
  }
}
</style>
