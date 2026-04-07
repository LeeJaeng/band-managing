<script setup lang="ts">
const { api } = useApi()
const { isAdmin } = useAuth()

const songs = ref<any[]>([])
const query = ref('')
const total = ref(0)
const loading = ref(false)

const selected = ref<string[]>([])
const merging = ref(false)

function isSelected(id: string) {
  return selected.value.includes(id)
}

function toggleSelect(id: string) {
  const idx = selected.value.indexOf(id)
  if (idx >= 0) selected.value.splice(idx, 1)
  else selected.value.push(id)
}

function clearSelection() {
  selected.value = []
}

const selectedSongs = computed(() => songs.value.filter(s => selected.value.includes(s.id)))

async function doMerge(sourceId: string, targetId: string) {
  const src = songs.value.find(s => s.id === sourceId)!
  const tgt = songs.value.find(s => s.id === targetId)!
  if (!confirm(`"${src.title}"의 레퍼런스/악보를 "${tgt.title}"에 합치고 원본을 삭제합니다.\n계속하시겠습니까?`)) return
  merging.value = true
  try {
    await api(`/api/admin/songs/merge?source_id=${sourceId}&target_id=${targetId}`, { method: 'POST' })
    clearSelection()
    await search()
  } catch (e: any) { alert(e.message || '병합 실패') }
  merging.value = false
}

async function search() {
  loading.value = true
  const data = await api<any>(`/api/songs?q=${encodeURIComponent(query.value)}&limit=100`)
  songs.value = data.items
  total.value = data.total
  loading.value = false
  clearSelection()
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
      <NuxtLink v-if="isAdmin" to="/songs/new" class="btn-accent">곡 등록</NuxtLink>
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
      <div
        v-for="s in songs"
        :key="s.id"
        class="song-card"
        :class="{ selected: isSelected(s.id) }"
      >
        <label v-if="isAdmin" class="checkbox-wrap" @click.prevent="toggleSelect(s.id)">
          <input type="checkbox" :checked="isSelected(s.id)" @change="toggleSelect(s.id)" />
        </label>
        <NuxtLink :to="`/songs/${s.id}`" class="song-info">
          <div class="song-title">{{ s.title }}</div>
          <div class="song-meta">
            <span v-if="s.default_key" class="key-badge">{{ s.default_key }}</span>
            <span class="ref-count">레퍼런스 {{ s.ref_count || 0 }}개</span>
          </div>
        </NuxtLink>
        <button v-if="isAdmin" class="btn-sm danger" @click="deleteSong($event, s.id, s.title)">삭제</button>
      </div>
    </div>

    <!-- 병합 바 (2개 선택 시) -->
    <Teleport to="body">
      <div v-if="isAdmin && selected.length >= 2" class="merge-bar">
        <button class="merge-bar-close" @click="clearSelection">✕</button>
        <span class="merge-bar-label">{{ selected.length }}개 선택됨 — 어떻게 병합할까요?</span>
        <div class="merge-bar-actions">
          <button
            class="merge-btn"
            :disabled="merging"
            @click="doMerge(selectedSongs[0].id, selectedSongs[1].id)"
          >
            <span class="merge-del">{{ selectedSongs[0].title }}</span>
            <span class="merge-arrow">→</span>
            <span class="merge-keep">{{ selectedSongs[1].title }}</span>
          </button>
          <button
            class="merge-btn"
            :disabled="merging"
            @click="doMerge(selectedSongs[1].id, selectedSongs[0].id)"
          >
            <span class="merge-del">{{ selectedSongs[1].title }}</span>
            <span class="merge-arrow">→</span>
            <span class="merge-keep">{{ selectedSongs[0].title }}</span>
          </button>
        </div>
        <span class="merge-bar-hint">삭제 → 남길 곡</span>
      </div>
    </Teleport>
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
  padding-bottom: 100px; // merge bar 공간
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
  &.selected { border-color: var(--accent); background: var(--accent-soft); }
}

.checkbox-wrap {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  cursor: pointer;

  input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--accent);
    cursor: pointer;
  }
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

// 병합 바
.merge-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--card);
  border: 1px solid var(--accent);
  border-radius: 16px;
  padding: 14px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  z-index: 200;
  min-width: 320px;
  max-width: 90vw;
}

.merge-bar-close {
  position: absolute;
  top: 10px; right: 14px;
  background: none; border: none;
  color: var(--text-dim); font-size: 14px; cursor: pointer;
  &:hover { color: var(--text); }
}

.merge-bar-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.merge-bar-hint {
  font-size: 11px;
  color: var(--text-dim);
}

.merge-bar-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.merge-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.03);
  cursor: pointer;
  font-size: 13px;
  width: 100%;
  text-align: left;
  transition: background .15s;
  &:hover:not(:disabled) { background: var(--accent-soft); border-color: var(--accent); }
  &:disabled { opacity: .5; cursor: not-allowed; }
}

.merge-del { color: var(--red); font-weight: 600; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.merge-arrow { color: var(--text-dim); flex-shrink: 0; }
.merge-keep { color: var(--green); font-weight: 600; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: right; }
</style>
