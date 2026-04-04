<script setup lang="ts">
const { api } = useApi()

const songs = ref<any[]>([])
const query = ref('')
const total = ref(0)
const loading = ref(true)

async function search() {
  loading.value = true
  const data = await api<any>(`/api/songs?q=${encodeURIComponent(query.value)}&limit=100`)
  songs.value = data.items
  total.value = data.total
  loading.value = false
}

onMounted(search)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>곡 DB</h1>
      <NuxtLink to="/songs/new" class="btn-accent">곡 등록</NuxtLink>
    </div>

    <div class="search-bar">
      <input
        v-model="query"
        class="input"
        placeholder="곡 제목 또는 가사로 검색..."
        @keyup.enter="search"
      />
      <button class="btn" @click="search">검색</button>
    </div>

    <p class="total">총 {{ total }}곡</p>

    <div v-if="loading" class="loading">불러오는 중...</div>

    <div v-else class="song-list">
      <NuxtLink
        v-for="s in songs"
        :key="s.id"
        :to="`/songs/${s.id}`"
        class="song-card"
      >
        <div class="song-title">{{ s.title }}</div>
        <div class="song-meta">
          <span v-if="s.artist">{{ s.artist }}</span>
          <span v-if="s.default_key" class="key-badge">{{ s.default_key }}</span>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h1 { font-size: 24px; font-weight: 800; margin: 0; }
}

.btn-accent { @include btn-accent; }

.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;

  .input { @include input; flex: 1; }
}

.btn { @include btn; }

.total {
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 16px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-dim);
}

.song-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.song-card {
  @include card;
  padding: 14px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: border-color .15s;

  &:hover { border-color: rgba(124,92,255,0.4); }
}

.song-title { font-weight: 600; }

.song-meta {
  display: flex;
  gap: 10px;
  font-size: 13px;
  color: var(--text-dim);
}

.key-badge {
  background: var(--accent-soft);
  color: var(--accent);
  padding: 1px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}
</style>
