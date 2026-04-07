<script setup lang="ts">
const { api } = useApi()
const { isAdmin } = useAuth()

const songs = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const PAGE_SIZE = 100

// 검색 & 필터
const query = ref('')
const filterKey = ref('')
const filterTempo = ref('')
const filterChannel = ref('')
const channels = ref<any[]>([])

const COMMON_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'Bb', 'B', 'C#', 'Eb', 'F#', 'Ab']

// 같은 이름 모아보기
const groupDuplicates = ref(false)

const displaySongs = computed(() => {
  if (!groupDuplicates.value) return songs.value
  // 제목 기준 그룹화, 2개 이상인 것만 모아 반환 (같은 제목끼리 붙어서)
  const groups = new Map<string, any[]>()
  for (const s of songs.value) {
    const key = s.title.trim().toLowerCase()
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(s)
  }
  const result: any[] = []
  for (const group of groups.values()) {
    if (group.length >= 2) result.push(...group)
  }
  return result
})

// 선택
const selected = ref<string[]>([])

function isSelected(id: string) { return selected.value.includes(id) }
function toggleSelect(id: string) {
  const idx = selected.value.indexOf(id)
  if (idx >= 0) selected.value.splice(idx, 1)
  else selected.value.push(id)
}
function clearSelection() { selected.value = []; bulkMode.value = null; mergeTarget.value = null }

const selectedSongs = computed(() => songs.value.filter(s => isSelected(s.id)))

// 병합 모드 (2개+ 선택 시)
const mergeTarget = ref<string | null>(null)  // 남길 곡 ID
const merging = ref(false)

function setMergeTarget(id: string) { mergeTarget.value = id }

async function doMerge() {
  if (!mergeTarget.value) { alert('남길 곡을 선택해주세요.'); return }
  const sources = selected.value.filter(id => id !== mergeTarget.value)
  const tgt = selectedSongs.value.find(s => s.id === mergeTarget.value)!
  const srcTitles = selectedSongs.value.filter(s => s.id !== mergeTarget.value).map(s => s.title).join(', ')
  if (!confirm(`"${srcTitles}"을 "${tgt.title}"에 합치고 원본을 삭제합니다.\n계속하시겠습니까?`)) return
  merging.value = true
  try {
    await api('/api/admin/songs/merge', {
      method: 'POST',
      body: JSON.stringify({ source_ids: sources, target_id: mergeTarget.value }),
    })
    mergeTarget.value = null
    clearSelection()
    await search()
  } catch (e: any) { alert(e.message || '병합 실패') }
  merging.value = false
}

// 일괄 편집 모드
const bulkMode = ref<'merge' | 'edit' | null>(null)
const bulkKeys = ref<string[]>([])
const bulkTempo = ref('')
const bulkBusy = ref(false)

function toggleBulkKey(k: string) {
  const idx = bulkKeys.value.indexOf(k)
  if (idx >= 0) bulkKeys.value.splice(idx, 1)
  else bulkKeys.value.push(k)
}

async function doBulkUpdate() {
  if (!bulkKeys.value.length && !bulkTempo.value) { alert('변경할 항목을 선택해주세요.'); return }
  bulkBusy.value = true
  try {
    await api('/api/admin/songs/bulk-update', {
      method: 'POST',
      body: JSON.stringify({
        song_ids: selected.value,
        add_keys: bulkKeys.value.length ? bulkKeys.value : null,
        set_tempo: bulkTempo.value || null,
      }),
    })
    bulkKeys.value = []
    bulkTempo.value = ''
    clearSelection()
    await search()
  } catch (e: any) { alert(e.message || '수정 실패') }
  bulkBusy.value = false
}

async function deleteSong(e: Event, songId: string, title: string) {
  e.preventDefault(); e.stopPropagation()
  if (!confirm(`"${title}" 곡을 삭제하시겠습니까?`)) return
  try {
    await api(`/api/songs/${songId}`, { method: 'DELETE' })
    await search()
  } catch (err: any) { alert(err.message || '삭제 실패') }
}

function buildSearchParams(offset: number) {
  const params = new URLSearchParams({
    q: query.value,
    limit: String(PAGE_SIZE),
    offset: String(offset),
  })
  if (filterKey.value === 'NO_KEY') params.set('no_key', 'true')
  else if (filterKey.value) params.set('key_filter', filterKey.value)
  if (filterTempo.value === 'NO_TEMPO') params.set('no_tempo', 'true')
  else if (filterTempo.value) params.set('tempo', filterTempo.value)
  if (filterChannel.value) params.set('channel_id', filterChannel.value)
  return params
}

async function search() {
  loading.value = true
  const params = buildSearchParams(0)
  const data = await api<any>(`/api/songs?${params}`)
  songs.value = data.items
  total.value = data.total
  loading.value = false
  clearSelection()
}

async function loadMore() {
  if (loadingMore.value) return
  if (songs.value.length >= total.value) return
  loadingMore.value = true
  try {
    const params = buildSearchParams(songs.value.length)
    const data = await api<any>(`/api/songs?${params}`)
    songs.value = [...songs.value, ...data.items]
    total.value = data.total
  } catch (e: any) {
    alert(e.message || '추가 로드 실패')
  }
  loadingMore.value = false
}

function resetFilters() {
  filterKey.value = ''; filterTempo.value = ''; filterChannel.value = ''; query.value = ''; groupDuplicates.value = false
  search()
}

onMounted(async () => {
  const [, ch] = await Promise.all([
    search(),
    api<any[]>('/api/channels').catch(() => []),
  ])
  channels.value = ch || []
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>곡 DB</h1>
      <NuxtLink v-if="isAdmin" to="/songs/new" class="btn-accent">곡 등록</NuxtLink>
    </div>

    <!-- 검색 & 필터 -->
    <div class="search-bar">
      <input v-model="query" class="input" placeholder="곡 제목 또는 가사로 검색..." @keyup.enter="search" />
      <button class="btn" @click="search">검색</button>
    </div>

    <div class="filter-bar">
      <select v-model="filterKey" class="filter-select" @change="search">
        <option value="">키 전체</option>
        <option value="NO_KEY">— 키 없음</option>
        <option v-for="k in COMMON_KEYS" :key="k" :value="k">{{ k }}</option>
      </select>
      <select v-model="filterTempo" class="filter-select" @change="search">
        <option value="">빠르기 전체</option>
        <option value="NO_TEMPO">— 빠르기 없음</option>
        <option value="FAST">빠른곡</option>
        <option value="SLOW">느린곡</option>
      </select>
      <select v-if="channels.length" v-model="filterChannel" class="filter-select" @change="search">
        <option value="">팀 전체</option>
        <option v-for="c in channels" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <label class="dup-check">
        <input type="checkbox" v-model="groupDuplicates" />
        <span>같은 이름 모아보기</span>
      </label>
      <button v-if="filterKey || filterTempo || filterChannel || groupDuplicates" class="filter-reset" @click="resetFilters">필터 초기화</button>
    </div>

    <p class="total">
      총 {{ total }}곡
      <span v-if="groupDuplicates"> · 중복 {{ displaySongs.length }}곡</span>
      <span v-if="selected.length" class="selected-count"> · {{ selected.length }}개 선택</span>
    </p>

    <div v-if="loading" class="loading">불러오는 중...</div>
    <div v-else-if="songs.length === 0" class="empty">등록된 곡이 없습니다.</div>

    <div v-else class="song-list">
      <template v-for="(s, idx) in displaySongs" :key="s.id">
        <!-- 같은 이름 모아보기: 그룹 첫 항목에 구분선 -->
        <div
          v-if="groupDuplicates && (idx === 0 || displaySongs[idx-1].title.trim().toLowerCase() !== s.title.trim().toLowerCase())"
          class="dup-group-label"
        >{{ s.title }}</div>
      <div
        class="song-card"
        :class="{ selected: isSelected(s.id) }"
      >
        <label v-if="isAdmin" class="checkbox-wrap" @click.stop>
          <input type="checkbox" :value="s.id" v-model="selected" />
        </label>
        <NuxtLink :to="`/songs/${s.id}`" class="song-info">
          <div class="song-title">{{ s.title }}</div>
          <div class="song-meta">
            <span v-if="s.default_key" class="key-badge">{{ s.default_key }}</span>
            <span v-for="k in (s.keys || []).filter((k:string) => k !== s.default_key)" :key="k" class="key-badge dim">{{ k }}</span>
            <span v-if="s.tempo" :class="['tempo-badge', s.tempo.toLowerCase()]">{{ s.tempo === 'FAST' ? '빠른곡' : '느린곡' }}</span>
            <span
              v-for="t in (s.refs_by_team || [])" :key="t.channel_id || 'none'"
              class="team-tag"
            >{{ t.channel_name }} {{ t.count }}</span>
            <span v-if="!(s.refs_by_team || []).length" class="ref-count">레퍼런스 없음</span>
          </div>
        </NuxtLink>
        <button v-if="isAdmin" class="btn-sm danger" @click="deleteSong($event, s.id, s.title)">삭제</button>
      </div>
      </template>
    </div>

    <div v-if="!loading && songs.length < total && !groupDuplicates" class="load-more-wrap">
      <button class="btn load-more" :disabled="loadingMore" @click="loadMore">
        {{ loadingMore ? '불러오는 중...' : `더보기 (${songs.length} / ${total})` }}
      </button>
    </div>

    <!-- 선택 액션 바 -->
    <Teleport to="body">
      <div v-if="isAdmin && selected.length >= 2" class="action-bar">
        <div class="action-bar-header">
          <button v-if="bulkMode" class="back-btn" @click="bulkMode = null">←</button>
          <span class="action-bar-label">
            {{ bulkMode === 'merge' ? '병합' : bulkMode === 'edit' ? '일괄 편집' : `${selected.length}개 선택됨` }}
          </span>
          <button class="action-bar-close" @click="clearSelection">✕</button>
        </div>

        <!-- 초기: 무엇을 할지 선택 -->
        <div v-if="!bulkMode" class="mode-select">
          <button class="mode-btn" @click="bulkMode = 'merge'">
            <span class="mode-icon">🔀</span>
            <span class="mode-text">
              <strong>병합</strong>
              <small>중복된 곡을 하나로 합치기</small>
            </span>
          </button>
          <button class="mode-btn" @click="bulkMode = 'edit'">
            <span class="mode-icon">✏️</span>
            <span class="mode-text">
              <strong>일괄 편집</strong>
              <small>키 추가, 빠르기 설정</small>
            </span>
          </button>
        </div>

        <!-- 병합 -->
        <div v-else-if="bulkMode === 'merge'" class="merge-panel">
          <p class="panel-hint">남길 곡을 클릭하여 선택하세요. 나머지는 삭제됩니다.</p>
          <div class="merge-songs">
            <div
              v-for="s in selectedSongs" :key="s.id"
              :class="['merge-song-item', { keep: mergeTarget === s.id }]"
              @click="setMergeTarget(s.id)"
            >
              <span class="merge-song-title">{{ s.title }}</span>
              <span v-if="mergeTarget === s.id" class="keep-badge">남길 곡</span>
              <span v-else class="del-badge">삭제</span>
            </div>
          </div>
          <button class="btn-accent" @click="doMerge" :disabled="merging || !mergeTarget">
            {{ merging ? '병합 중...' : '병합 실행' }}
          </button>
        </div>

        <!-- 일괄 편집 -->
        <div v-else class="edit-panel">
          <div class="edit-section">
            <p class="panel-hint">추가할 키 선택 (기존 키에 추가됩니다)</p>
            <div class="key-chips">
              <button
                v-for="k in COMMON_KEYS" :key="k"
                :class="['key-chip', { selected: bulkKeys.includes(k) }]"
                @click="toggleBulkKey(k)"
              >{{ k }}</button>
            </div>
          </div>
          <div class="edit-section">
            <p class="panel-hint">빠르기 설정</p>
            <div class="tempo-btns">
              <button :class="['tempo-btn', { active: bulkTempo === 'FAST' }]" @click="bulkTempo = bulkTempo === 'FAST' ? '' : 'FAST'">빠른곡</button>
              <button :class="['tempo-btn slow', { active: bulkTempo === 'SLOW' }]" @click="bulkTempo = bulkTempo === 'SLOW' ? '' : 'SLOW'">느린곡</button>
            </div>
          </div>
          <button class="btn-accent" @click="doBulkUpdate" :disabled="bulkBusy">
            {{ bulkBusy ? '적용 중...' : `${selected.length}개 곡에 적용` }}
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

.page-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
  h1 { font-size: 24px; font-weight: 800; margin: 0; }
}

.btn { @include btn; }
.btn-accent { @include btn-accent; }

.search-bar {
  display: flex; gap: 8px; margin-bottom: 10px;
  .input { @include input; flex: 1; }
}

.filter-bar {
  display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center;
}
.filter-select {
  @include input;
  width: auto; height: 38px;
  padding: 0 10px; font-size: 13px;
  appearance: auto; flex: 0 0 auto;
}
.filter-reset {
  background: none; border: none; color: var(--text-dim); font-size: 12px;
  cursor: pointer; padding: 0 4px;
  &:hover { color: var(--accent); }
}

.total { font-size: 13px; color: var(--text-dim); margin-bottom: 16px; }
.selected-count { color: var(--accent); font-weight: 700; }

.loading, .empty { text-align: center; padding: 40px; color: var(--text-dim); }

.song-list { display: flex; flex-direction: column; gap: 8px; padding-bottom: 120px; }

.load-more-wrap { display: flex; justify-content: center; margin: 16px 0 140px; }
.load-more { min-width: 200px; padding: 12px 24px; font-size: 14px; }

.dup-group-label {
  font-size: 12px; font-weight: 700; color: var(--accent);
  padding: 12px 4px 4px; border-bottom: 1px solid var(--line);
  margin-bottom: 2px;
  &:first-child { padding-top: 0; }
}

.dup-check {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--text-dim); cursor: pointer;
  input[type="checkbox"] { accent-color: var(--accent); width: 14px; height: 14px; cursor: pointer; }
  &:hover { color: var(--text); }
}

.song-card {
  @include card; padding: 14px 16px;
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  transition: border-color .15s;
  &:hover { border-color: rgba(139,111,255,0.4); }
  &.selected { border-color: var(--accent); background: rgba(139,111,255,0.06); }
}

.checkbox-wrap {
  display: flex; align-items: center; flex-shrink: 0; cursor: pointer;
  input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }
}

.song-info { flex: 1; min-width: 0; text-decoration: none; color: inherit; }
.song-title { font-weight: 600; margin-bottom: 4px; }
.song-meta { display: flex; gap: 8px; font-size: 13px; color: var(--text-dim); flex-wrap: wrap; align-items: center; }

.key-badge {
  background: var(--accent-soft); color: var(--accent);
  padding: 1px 8px; border-radius: 6px; font-size: 12px; font-weight: 700;
  &.dim { opacity: 0.6; }
}
.tempo-badge {
  padding: 1px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;
  &.fast { background: rgba(255,100,80,0.15); color: #ff6450; }
  &.slow { background: rgba(80,150,255,0.15); color: #5096ff; }
}
.ref-count { font-size: 12px; }
.team-tag {
  background: rgba(255,255,255,0.05); color: var(--text-dim);
  padding: 1px 8px; border-radius: 6px; font-size: 11px;
  border: 1px solid var(--line);
}

.btn-sm {
  padding: 4px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: rgba(255,255,255,0.02); color: var(--text); font-size: 12px;
  cursor: pointer; flex-shrink: 0;
  &:hover { background: rgba(255,255,255,0.05); }
  &.danger { color: var(--red); &:hover { background: var(--red-soft); } }
}

// 선택 액션 바
.action-bar {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: var(--card); border: 1px solid var(--accent); border-radius: 16px;
  padding: 16px 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  z-index: 200; min-width: 340px; max-width: 92vw;
  display: flex; flex-direction: column; gap: 12px;
}

.action-bar-header {
  display: flex; align-items: center; gap: 8px;
}
.action-bar-label { font-size: 13px; font-weight: 700; flex: 1; }
.action-bar-close {
  background: none; border: none; color: var(--text-dim); font-size: 14px; cursor: pointer;
  &:hover { color: var(--text); }
}
.back-btn {
  background: none; border: none; color: var(--text-dim); font-size: 16px;
  cursor: pointer; padding: 0 4px;
  &:hover { color: var(--text); }
}

.mode-select { display: flex; flex-direction: column; gap: 8px; }
.mode-btn {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border-radius: 10px; border: 1px solid var(--line);
  background: rgba(255,255,255,0.02); cursor: pointer; text-align: left;
  transition: all .15s;
  &:hover { border-color: var(--accent); background: var(--accent-soft); }
}
.mode-icon { font-size: 20px; flex-shrink: 0; }
.mode-text {
  display: flex; flex-direction: column; gap: 2px;
  strong { font-size: 14px; color: var(--text); }
  small { font-size: 12px; color: var(--text-dim); }
}

.panel-hint { font-size: 12px; color: var(--text-dim); margin: 0 0 8px; }

.merge-panel, .edit-panel { display: flex; flex-direction: column; gap: 10px; }

.merge-songs { display: flex; flex-direction: column; gap: 6px; }
.merge-song-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: 10px; border: 1px solid var(--line);
  cursor: pointer; transition: all .15s;
  &:hover { border-color: var(--accent); }
  &.keep { border-color: var(--green); background: rgba(80,200,120,0.08); }
}
.merge-song-title { flex: 1; font-size: 13px; font-weight: 600; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.keep-badge { font-size: 11px; font-weight: 700; color: var(--green); flex-shrink: 0; }
.del-badge { font-size: 11px; color: var(--text-dim); flex-shrink: 0; }

.edit-section { display: flex; flex-direction: column; gap: 6px; }
.key-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.key-chip {
  padding: 4px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: rgba(255,255,255,0.02); color: var(--text-dim);
  font-size: 12px; font-weight: 600; cursor: pointer;
  &.selected { background: var(--accent); border-color: var(--accent); color: #fff; }
}
.tempo-btns { display: flex; gap: 8px; }
.tempo-btn {
  padding: 6px 16px; border-radius: 8px; border: 1px solid var(--line);
  background: none; font-size: 13px; cursor: pointer; color: var(--text-dim);
  &.active { background: rgba(255,100,80,0.15); border-color: #ff6450; color: #ff6450; }
  &.slow.active { background: rgba(80,150,255,0.15); border-color: #5096ff; color: #5096ff; }
}

@media (max-width: 640px) {
  .filter-bar { gap: 6px; }
  .filter-select { font-size: 12px; }
  .action-bar { bottom: 12px; min-width: calc(100vw - 32px); }
}
</style>
