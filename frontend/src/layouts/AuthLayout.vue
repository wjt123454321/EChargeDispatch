<template>
  <div class="auth-layout">
    <div class="auth-layout__brand">
      <div class="brand-content">
        <div class="brand-logo">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="10" fill="rgba(255,255,255,0.12)"/>
            <path d="M14 12h4l6 14v-8h4l-8 16v-10h-4l2-12z" fill="#e8a838"/>
          </svg>
        </div>
        <h1 class="brand-title">ECharge</h1>
        <p class="brand-subtitle">智能充电桩调度计费系统</p>
        <div class="brand-features">
          <div class="feature">
            <span class="feature__icon">⚡</span>
            <div>
              <strong>智能调度</strong>
              <p>最短等待时间优化分配</p>
            </div>
          </div>
          <div class="feature">
            <span class="feature__icon">📊</span>
            <div>
              <strong>分时计费</strong>
              <p>峰谷平时段自动计价</p>
            </div>
          </div>
          <div class="feature">
            <span class="feature__icon">🔧</span>
            <div>
              <strong>运维监控</strong>
              <p>实时桩状态与故障处理</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="auth-layout__form">
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </div>
  </div>
</template>

<style scoped>
.auth-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
}

.auth-layout__brand {
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  position: relative;
  overflow: hidden;
}

.auth-layout__brand::before {
  content: '';
  position: absolute;
  top: -30%;
  right: -20%;
  width: 60%;
  height: 80%;
  background: radial-gradient(ellipse, rgba(232, 168, 56, 0.15) 0%, transparent 70%);
  pointer-events: none;
}

.brand-content {
  max-width: 380px;
  position: relative;
  z-index: 1;
}

.brand-logo {
  margin-bottom: 20px;
}

.brand-title {
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.brand-subtitle {
  margin-top: 8px;
  font-size: 0.9375rem;
  opacity: 0.75;
}

.brand-features {
  margin-top: 48px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.feature {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.feature__icon {
  font-size: 1.25rem;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.feature strong {
  display: block;
  font-size: 0.875rem;
  margin-bottom: 2px;
}

.feature p {
  font-size: 0.8125rem;
  opacity: 0.65;
}

.auth-layout__form {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: var(--color-bg);
}

@media (max-width: 900px) {
  .auth-layout {
    grid-template-columns: 1fr;
  }

  .auth-layout__brand {
    display: none;
  }

  .auth-layout__form {
    min-height: 100vh;
    min-height: 100dvh;
    padding: 24px 20px;
    padding-top: calc(24px + env(safe-area-inset-top, 0px));
    padding-bottom: calc(24px + env(safe-area-inset-bottom, 0px));
    align-items: flex-start;
    padding-top: max(48px, calc(24px + env(safe-area-inset-top, 0px)));
  }
}
</style>
