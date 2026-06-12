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
        <nav class="header__nav header__nav--desktop">
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
        <button class="logout-btn" type="button" @click="handleLogout">退出</button>
      </div>
    </header>

    <main class="main">
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>

    <nav class="bottom-nav" aria-label="主导航">
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
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  min-height: 100dvh;
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
  padding: 0 16px;
  padding-top: env(safe-area-inset-top, 0px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header__left {
  display: flex;
  align-items: center;
  gap: 32px;
  min-width: 0;
}

.header__logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
  font-size: 1rem;
  color: var(--color-text);
  text-decoration: none;
  flex-shrink: 0;
}

.header__logo span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header__nav--desktop {
  display: none;
}

.header__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.user-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 5px 10px;
  background: var(--color-surface-muted);
  border-radius: 100px;
  color: var(--color-text-secondary);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-muted);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.logout-btn:hover {
  color: var(--color-danger);
  background: rgba(184, 58, 58, 0.08);
}

.main {
  flex: 1;
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
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  text-decoration: none;
  color: var(--color-text-muted);
  font-size: 0.6875rem;
  font-weight: 600;
  transition: color var(--transition-fast);
}

.bottom-nav__item--active {
  color: var(--color-primary);
}

.bottom-nav__icon {
  font-size: 1.125rem;
  line-height: 1;
}

.bottom-nav__label {
  line-height: 1.2;
}

@media (min-width: 769px) {
  .header {
    padding: 0 28px;
  }

  .header__logo {
    font-size: 1.0625rem;
    gap: 10px;
  }

  .user-badge {
    font-size: 0.8125rem;
    padding: 6px 14px;
    max-width: none;
  }

  .bottom-nav {
    display: none;
  }

  .header__nav--desktop {
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

  .main :deep(.page) {
    padding-bottom: 32px;
  }
}
</style>
