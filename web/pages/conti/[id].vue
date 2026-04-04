<script setup lang="ts">
const route = useRoute()
const { api } = useApi()

const conti = ref<any>(null)
const loading = ref(true)
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const searching = ref(false)

async function load() {
  loading.value = true
  conti.value = await api<any>(`/api/contis/${route.params.id}`)
  loading.value = false
}

async function searchSongs() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  const data = await api<any>(`/api/songs?q=${encodeURIComponent(searchQuery.value)}`)
  searchResults.value = data.items
  searching.value = false
}

async function addSong(song: any) {
  const nextOrder = (conti.value.items?.length || 0) + 1
  await api('/api/contis/' + route.params.id + '/items', {
    method: 'POST',
    body: JSON.stringify({
      song_id: song.id,
      order_num: nextOrder,
      slot_label: `${nextOrder}번곡`,
    }),
  })
  searchQuery.value = ''
  searchResults.value = []
  await load()
}

async function removeItem(itemId: string) {
  await api(`/api/contis/items/${itemId}`, { method: 'DELETE' })
  await load()
}

async function confirmConti() {
  await api(`/api/contis/${route.params.id}/confirm`, { method: 'PUT' })
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div v-if="loading" class="loading">불러오는 중...</div>

    <template v-else-if="conti">
      <div class="conti-header">
        <div>
          <h1>{{ conti.service_name }}</h1>
          <p class="meta">{{ conti.date }} &middot; {{ conti.author }}</p>
        </div>
        <div class="header-actions">
          <span :class="['status-badge', conti.status.toLowerCase()]">
            {{ conti.status === 'CONFIRMED' ? '확정' : '작성중' }}
          </span>
          <button v-if="conti.status === 'DRAFT'" class="btn-accent" @click="confirmConti">확정</button>
        </div>
      </div>

      <!-- 곡 목록 -->
      <div class="items">
        <div v-for="item in conti.items" :key="item.id" class="item-card">
          <div class="item-order">{{ item.slot_label || item.order_num }}</div>
          <div class="item-info">
            <div class="item-title">{{ item.song?.title }}</div>
            <div class="item-detail">
              <span v-if="item.use_key || item.song?.default_key" class="key-badge">
                {{ item.use_key || item.song?.default_key }}
              </span>
              <span v-if="item.reference" class="ref-link">
                <a :href="item.reference.youtube_url" target="_blank">{{ item.reference.title }}</a>
              </span>
              <span v-if="item.memo" class="memo">{{ item.memo }}</span>
            </div>
          </div>
          <button class="btn-remove" @click="removeItem(item.id)">x</button>
        </div>

        <div v-if="conti.items.length === 0" class="empty">
          곡을 추가해주세요
        </div>
      </div>

      <!-- 곡 검색/추가 -->
      <div class="search-section">
        <h3>곡 추가</h3>
        <div class="search-bar">
          <input
            v-model="searchQuery"
            class="input"
            placeholder="곡 제목 검색..."
            @keyup.enter="searchSongs"
          />
          <button class="btn" @click="searchSongs">검색</button>
        </div>

        <div v-if="searching" class="loading-sm">검색 중...</div>

        <div v-if="searchResults.length > 0" class="search-results">
          <div
            v-for="song in searchResults"
            :key="song.id"
            class="search-item"
            @click="addSong(song)"
          >
            <span class="song-title">{{ song.title }}</span>
            <span v-if="song.default_key" class="key-badge">{{ song.default_key }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

.conti-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;

  h1 { font-size: 24px; font-weight: 800; margin: 0 0 4px; }
  .meta { font-size: 14px; color: var(--text-dim); margin: 0; }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  &.draft { background: var(--accent-soft); color: var(--accent); }
  &.confirmed { background: var(--green-soft); color: var(--green); }
}

.btn { @include btn; }
.btn-accent { @include btn-accent; }
.input { @include input; }

.items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 32px;
}

.item-card {
  @include card;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.item-order {
  min-width: 60px;
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
}

.item-info {
  flex: 1;
}

.item-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.item-detail {
  display: flex;
  gap: 10px;
  font-size: 13px;
  color: var(--text-dim);
  flex-wrap: wrap;
}

.key-badge {
  background: var(--accent-soft);
  color: var(--accent);
  padding: 1px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}

.ref-link a {
  color: var(--green);
  &:hover { text-decoration: underline; }
}

.btn-remove {
  @include btn;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
  font-size: 14px;
  color: var(--red);
  &:hover { background: var(--red-soft); }
}

.empty {
  text-align: center;
  padding: 40px;
  color: var(--text-dim);
}

.search-section {
  @include card;
  padding: 20px;

  h3 {
    font-size: 16px;
    font-weight: 700;
    margin: 0 0 12px;
  }
}

.search-bar {
  display: flex;
  gap: 8px;

  .input { flex: 1; }
}

.loading, .loading-sm {
  text-align: center;
  color: var(--text-dim);
  padding: 20px;
}

.search-results {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.search-item {
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: background .1s;

  &:hover { background: rgba(255,255,255,0.05); }

  .song-title { font-weight: 600; }
  .song-artist { font-size: 13px; color: var(--text-dim); }
}

.memo {
  font-style: italic;
}
</style>
