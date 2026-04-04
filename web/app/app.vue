<template>
  <div id="app">
    <nav class="nav">
      <NuxtLink to="/" class="nav-brand">Band Managing</NuxtLink>
      <div class="nav-links">
        <NuxtLink to="/">콘티</NuxtLink>
        <NuxtLink to="/songs">곡 DB</NuxtLink>
        <NuxtLink to="/admin">관리자</NuxtLink>
      </div>
    </nav>
    <main class="main">
      <NuxtPage />
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
  gap: 20px;

  a {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-dim);
    transition: color .15s;
    &:hover, &.router-link-active { color: var(--text); }
  }
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
