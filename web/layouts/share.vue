<template>
  <div id="app">
    <nav class="share-nav">
      <NuxtLink to="/" class="nav-brand">Band Managing</NuxtLink>
    </nav>
    <main class="share-main">
      <slot />
    </main>
  </div>
</template>

<style lang="scss">
.share-nav {
  display: flex;
  align-items: center;
  padding: 0 16px;
  height: 48px;
  border-bottom: 1px solid var(--line);
  background: rgba(0,0,0,0.3);
  backdrop-filter: blur(12px);
}

.share-main {
  max-width: 640px;
  margin: 0 auto;
  padding: 20px 16px;
}
</style>
