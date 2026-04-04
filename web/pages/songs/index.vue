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

async function deleteSong(e: Event, songId: string, title: string) {
  e.preventDefault()
  e.stopPropagation()
  if (!confirm(`"${title}" 곡을 삭제하시겠습니까?`)) return
  try {
    await api(`/api/songs/${songId}`, { method: 'DELETE' })
    await search()
  } catch (err: any) { alert(err.message || '삭제 실패') }
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

    <div v-else-if="songs.length === 0" class="empty">등록된 곡이 없습니다.</div>

    <div v-else class="song-list">
      <div v-for="s in songs" :key="s.id" class="song-card">
        <NuxtLink :to="`/songs/${s.id}`" class="song-info">
          <div class="song-title">{{ s.title }}</div>
          <div class="song-meta">
            <span v-if="s.default_key" class="key-badge">{{ s.default_key }}</span>
            <span class="ref-count">레퍼런스 {{ s.ref_count || 0 }}개</span>
          </div>
        </NuxtLink>
        <button class="btn-sm danger" @click="deleteSong($event, s.id, s.title)">삭제</button>
      </div>
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

.btn { @include btn; }
.btn-accent { @include btn-accent; }

.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  .input { @include input; flex: 1; }
}

.total {
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 16px;
}

.loading, .empty {
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
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  transition: border-color .15s;
  &:hover { border-color: rgba(139,111,255,0.4); }
}

.song-info {
  flex: 1;
  min-width: 0;
  text-decoration: none;
  color: inherit;
}

.song-title { font-weight: 600; margin-bottom: 4px; }

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

.ref-count { font-size: 12px; }

.btn-sm {
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.02);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
  &:hover { background: rgba(255,255,255,0.05); }
  &.danger { color: var(--red); &:hover { background: var(--red-soft); } }
}
</style>
