<script setup lang="ts">
const { isLoggedIn, isAdmin, user, logout, fetchUser } = useAuth()

onMounted(async () => {
  if (isLoggedIn.value && !user.value) {
    await fetchUser()
  }
})
</script>

<template>
  <div id="app">
    <nav class="nav">
      <NuxtLink to="/" class="nav-brand">Band Managing</NuxtLink>
      <div class="nav-links">
        <NuxtLink to="/">콘티</NuxtLink>
        <NuxtLink to="/songs">곡 DB</NuxtLink>
        <NuxtLink v-if="isAdmin" to="/admin">관리자</NuxtLink>
        <template v-if="isLoggedIn">
          <button class="nav-logout" @click="logout">로그아웃</button>
        </template>
        <NuxtLink v-else to="/login" class="nav-login">로그인</NuxtLink>
      </div>
    </nav>
    <main class="main">
      <slot />
    </main>
  </div>
</template>

<style lang="scss">
.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 56px;
  border-bottom: 1px solid var(--line);
  background: rgba(0,0,0,0.3);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-weight: 800;
  font-size: 18px;
  color: var(--accent);
}

.nav-links {
  display: flex;
  gap: 16px;
  align-items: center;

  a {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-dim);
    white-space: nowrap;
    transition: color .15s;
    &:hover, &.router-link-active { color: var(--text); }
  }

  @media (max-width: 640px) {
    gap: 10px;
    a, .nav-user, .nav-logout { font-size: 12px; }
  }
}

.nav-user {
  font-size: 13px;
  color: var(--text-dim);
}

.nav-logout {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  &:hover { color: var(--red); }
}

.nav-login {
  font-size: 14px;
  font-weight: 600;
  color: var(--accent) !important;
}

.main {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 16px;

  @media (max-width: 640px) {
    padding: 16px 12px;
  }
}
</style>
