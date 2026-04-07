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

// ─────────────────────────────────────────────
// 곡 상세 모달 (편집 + 레퍼런스 + 가사 + 삭제)
// ─────────────────────────────────────────────
const ALL_KEYS_GROUPS = {
  common: ['C', 'D', 'E', 'F', 'G', 'A', 'Bb', 'B'],
  major: ['C#', 'Db', 'D#', 'Eb', 'F#', 'Gb', 'G#', 'Ab', 'A#'],
  minor: ['Am', 'Bm', 'Cm', 'C#m', 'Dm', 'D#m', 'Ebm', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'A#m', 'Bbm'],
}

const detailSong = ref<any>(null)        // 모달에서 표시중인 풀 데이터 (refs/sheets 포함)
const detailListIdx = ref<number>(-1)     // songs.value 내 인덱스 (인플레이스 갱신용)
const detailLoading = ref(false)
const detailEditing = ref(false)
const detailForm = ref({ title: '', keys: [] as string[], tempo: '', lyrics: '' })
const detailSaving = ref(false)
const showAllKeys = ref(false)
const showAddRef = ref(false)
const newRef = ref({ youtube_url: '', title: '', key: '' })
const playingRefId = ref<string | null>(null)

function playRef(refId: string) {
  playingRefId.value = playingRefId.value === refId ? null : refId
}

async function openDetail(e: Event, s: any) {
  e?.preventDefault?.()
  e?.stopPropagation?.()
  detailListIdx.value = songs.value.findIndex((x: any) => x.id === s.id)
  detailSong.value = { ...s, references: [], sheets: [] }
  detailEditing.value = false
  showAddRef.value = false
  showAllKeys.value = false
  playingRefId.value = null
  detailLoading.value = true
  try {
    detailSong.value = await api<any>(`/api/songs/${s.id}?_t=${Date.now()}`)
  } catch (err: any) {
    alert(err.message || '곡 정보 불러오기 실패')
    closeDetail()
  }
  detailLoading.value = false
}

function closeDetail() {
  detailSong.value = null
  detailListIdx.value = -1
  detailEditing.value = false
  showAddRef.value = false
  playingRefId.value = null
}

function syncListItem(patch: Record<string, any>) {
  if (detailListIdx.value < 0) return
  const cur = songs.value[detailListIdx.value]
  if (!cur) return
  songs.value[detailListIdx.value] = { ...cur, ...patch }
}

function startDetailEdit() {
  if (!detailSong.value) return
  detailForm.value = {
    title: detailSong.value.title || '',
    keys: [...(detailSong.value.keys || [])],
    tempo: detailSong.value.tempo || '',
    lyrics: detailSong.value.lyrics || '',
  }
  detailEditing.value = true
}

function toggleDetailKey(k: string) {
  const idx = detailForm.value.keys.indexOf(k)
  if (idx >= 0) detailForm.value.keys.splice(idx, 1)
  else detailForm.value.keys.push(k)
}

async function saveDetailEdit() {
  if (!detailSong.value) return
  const title = detailForm.value.title.trim()
  if (!title) { alert('제목을 입력해주세요.'); return }
  detailSaving.value = true
  try {
    await api(`/api/songs/${detailSong.value.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        title,
        keys: detailForm.value.keys,
        tempo: detailForm.value.tempo || null,
        lyrics: detailForm.value.lyrics,
      }),
    })
    detailSong.value.title = title
    detailSong.value.keys = [...detailForm.value.keys]
    detailSong.value.tempo = detailForm.value.tempo || null
    detailSong.value.lyrics = detailForm.value.lyrics
    syncListItem({
      title,
      keys: [...detailForm.value.keys],
      tempo: detailForm.value.tempo || null,
      lyrics: detailForm.value.lyrics,
    })
    detailEditing.value = false
  } catch (e: any) {
    alert(e.message || '저장 실패')
  }
  detailSaving.value = false
}

// 인라인 키 토글 (편집 모드 없이)
async function toggleKeyInline(key: string) {
  if (!detailSong.value) return
  const cur = [...(detailSong.value.keys || [])]
  const idx = cur.indexOf(key)
  if (idx >= 0) cur.splice(idx, 1)
  else cur.push(key)
  try {
    await api(`/api/songs/${detailSong.value.id}`, {
      method: 'PUT',
      body: JSON.stringify({ title: detailSong.value.title, keys: cur }),
    })
    detailSong.value.keys = cur
    syncListItem({ keys: [...cur] })
  } catch (e: any) { alert(e.message || '키 저장 실패') }
}

async function setTempoInline(tempo: string) {
  if (!detailSong.value) return
  const next = detailSong.value.tempo === tempo ? null : tempo
  try {
    await api(`/api/songs/${detailSong.value.id}`, {
      method: 'PUT',
      body: JSON.stringify({ title: detailSong.value.title, keys: detailSong.value.keys || [], tempo: next }),
    })
    detailSong.value.tempo = next
    syncListItem({ tempo: next })
  } catch (e: any) { alert(e.message || '빠르기 저장 실패') }
}

function extractVideoId(url: string): string {
  const match = url.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
  return match ? match[1] : ''
}

async function addReference() {
  if (!detailSong.value || !newRef.value.youtube_url) return
  const videoId = extractVideoId(newRef.value.youtube_url)
  if (!videoId) { alert('유효한 유튜브 URL을 입력해주세요.'); return }
  try {
    await api(`/api/songs/${detailSong.value.id}/references`, {
      method: 'POST',
      body: JSON.stringify({
        youtube_url: newRef.value.youtube_url,
        youtube_video_id: videoId,
        title: newRef.value.title || detailSong.value.title,
        key: newRef.value.key || null,
        source: 'MANUAL',
        trust_level: 'HIGH',
      }),
    })
    newRef.value = { youtube_url: '', title: '', key: '' }
    showAddRef.value = false
    // 상세 데이터만 다시 로드 (refs 동기화 위해)
    detailSong.value = await api<any>(`/api/songs/${detailSong.value.id}?_t=${Date.now()}`)
  } catch (e: any) { alert(e.message || '추가 실패') }
}

async function deleteReference(refId: string) {
  if (!confirm('레퍼런스를 삭제하시겠습니까?')) return
  try {
    await api(`/api/songs/references/${refId}`, { method: 'DELETE' })
    if (detailSong.value) {
      detailSong.value.references = (detailSong.value.references || []).filter((r: any) => r.id !== refId)
      detailSong.value.sheets = (detailSong.value.sheets || []).filter((s: any) => s.reference_id !== refId)
    }
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

async function deleteSheet(sheetId: string) {
  if (!confirm('악보를 삭제하시겠습니까?')) return
  try {
    await api(`/api/songs/sheets/${sheetId}`, { method: 'DELETE' })
    if (detailSong.value) {
      detailSong.value.sheets = (detailSong.value.sheets || []).filter((s: any) => s.id !== sheetId)
    }
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

async function deleteSong(e: Event | null, songId: string, title: string) {
  e?.preventDefault?.()
  e?.stopPropagation?.()
  if (!confirm(`"${title}" 곡을 삭제하시겠습니까?`)) return
  try {
    await api(`/api/songs/${songId}`, { method: 'DELETE' })
    songs.value = songs.value.filter((s: any) => s.id !== songId)
    total.value = Math.max(0, total.value - 1)
    if (detailSong.value && detailSong.value.id === songId) closeDetail()
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
        @click="openDetail($event, s)"
      >
        <label v-if="isAdmin" class="checkbox-wrap" @click.stop>
          <input type="checkbox" :value="s.id" v-model="selected" />
        </label>
        <div class="song-info">
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
        </div>
        <div v-if="isAdmin" class="card-actions" @click.stop>
          <button class="btn-sm danger" @click="deleteSong($event, s.id, s.title)">삭제</button>
        </div>
      </div>
      </template>
    </div>

    <!-- 곡 상세 모달 -->
    <Teleport to="body">
      <div v-if="detailSong" class="modal-overlay" @click.self="closeDetail">
        <div class="modal-panel detail-panel">
          <div class="modal-header">
            <h3>{{ detailEditing ? '곡 편집' : (detailSong.title || '곡 상세') }}</h3>
            <div class="header-actions">
              <button v-if="isAdmin && !detailEditing" class="btn-sm" @click="startDetailEdit">편집</button>
              <button v-if="isAdmin && !detailEditing" class="btn-sm danger" @click="deleteSong(null, detailSong.id, detailSong.title)">삭제</button>
              <button class="btn-sm" @click="closeDetail">닫기</button>
            </div>
          </div>

          <div v-if="detailLoading" class="detail-loading">불러오는 중...</div>

          <template v-else>
            <!-- 편집 모드 -->
            <div v-if="detailEditing" class="detail-edit">
              <label class="field-label">제목</label>
              <input v-model="detailForm.title" class="input" />

              <label class="field-label">키 (복수 선택)</label>
              <div class="key-chips">
                <button
                  v-for="k in ALL_KEYS_GROUPS.common" :key="k"
                  type="button"
                  :class="['key-chip', { selected: detailForm.keys.includes(k) }]"
                  @click="toggleDetailKey(k)"
                >{{ k }}</button>
              </div>
              <button class="lyrics-toggle" @click="showAllKeys = !showAllKeys">
                {{ showAllKeys ? '기타 키 접기' : '기타 키 더보기' }}
              </button>
              <div v-if="showAllKeys" class="key-chips">
                <button
                  v-for="k in [...ALL_KEYS_GROUPS.major, ...ALL_KEYS_GROUPS.minor]" :key="k"
                  type="button"
                  :class="['key-chip', { selected: detailForm.keys.includes(k) }]"
                  @click="toggleDetailKey(k)"
                >{{ k }}</button>
              </div>

              <label class="field-label">빠르기</label>
              <div class="tempo-row">
                <button
                  type="button"
                  :class="['tempo-btn', { active: detailForm.tempo === 'FAST' }]"
                  @click="detailForm.tempo = detailForm.tempo === 'FAST' ? '' : 'FAST'"
                >빠른곡</button>
                <button
                  type="button"
                  :class="['tempo-btn slow', { active: detailForm.tempo === 'SLOW' }]"
                  @click="detailForm.tempo = detailForm.tempo === 'SLOW' ? '' : 'SLOW'"
                >느린곡</button>
              </div>

              <label class="field-label">가사 / 송폼</label>
              <textarea v-model="detailForm.lyrics" class="textarea" rows="10" placeholder="[Verse 1]&#10;가사..." />

              <div class="modal-actions">
                <button class="btn-accent" :disabled="detailSaving" @click="saveDetailEdit">
                  {{ detailSaving ? '저장 중...' : '저장' }}
                </button>
                <button class="btn-sm" @click="detailEditing = false">취소</button>
              </div>
            </div>

            <!-- 보기 모드 -->
            <template v-else>
              <!-- 키 (인라인) -->
              <div class="detail-section">
                <div class="detail-section-title">키</div>
                <div class="key-inline">
                  <span v-for="k in (detailSong.keys || [])" :key="k" class="key-badge removable" @click="toggleKeyInline(k)">{{ k }} ×</span>
                  <span v-if="detailSong.default_key && !(detailSong.keys || []).includes(detailSong.default_key)" class="key-badge dim">{{ detailSong.default_key }}</span>
                </div>
                <div class="key-chips" style="margin-top: 8px;">
                  <button
                    v-for="k in ALL_KEYS_GROUPS.common" :key="k"
                    type="button"
                    :class="['key-chip', { selected: (detailSong.keys || []).includes(k) }]"
                    @click="toggleKeyInline(k)"
                  >{{ k }}</button>
                </div>
                <button class="lyrics-toggle" @click="showAllKeys = !showAllKeys">
                  {{ showAllKeys ? '기타 키 접기' : '기타 키 더보기' }}
                </button>
                <div v-if="showAllKeys" class="key-chips">
                  <button
                    v-for="k in [...ALL_KEYS_GROUPS.major, ...ALL_KEYS_GROUPS.minor]" :key="k"
                    type="button"
                    :class="['key-chip', { selected: (detailSong.keys || []).includes(k) }]"
                    @click="toggleKeyInline(k)"
                  >{{ k }}</button>
                </div>
              </div>

              <!-- 빠르기 (인라인) -->
              <div class="detail-section">
                <div class="detail-section-title">빠르기</div>
                <div class="tempo-row">
                  <button
                    type="button"
                    :class="['tempo-btn', { active: detailSong.tempo === 'FAST' }]"
                    @click="setTempoInline('FAST')"
                  >빠른곡</button>
                  <button
                    type="button"
                    :class="['tempo-btn slow', { active: detailSong.tempo === 'SLOW' }]"
                    @click="setTempoInline('SLOW')"
                  >느린곡</button>
                </div>
              </div>

              <!-- 레퍼런스 -->
              <div class="detail-section">
                <div class="detail-section-title">
                  레퍼런스 ({{ (detailSong.references || []).length }})
                  <button class="btn-sm" @click="showAddRef = !showAddRef">+ 추가</button>
                </div>

                <div v-if="showAddRef" class="add-ref-form">
                  <input v-model="newRef.youtube_url" class="input" placeholder="유튜브 URL" />
                  <div class="ref-sub">
                    <input v-model="newRef.title" class="input" placeholder="제목 (비우면 곡 제목)" />
                    <input v-model="newRef.key" class="input input-sm" placeholder="키" />
                  </div>
                  <button class="btn-accent btn-sm" @click="addReference">추가</button>
                </div>

                <div v-if="!(detailSong.references || []).length" class="empty-sm">레퍼런스 없음</div>
                <div v-for="ref in (detailSong.references || [])" :key="ref.id" class="ref-card">
                  <div v-if="ref.youtube_video_id || ref.thumbnail_url" class="ref-media">
                    <iframe
                      v-if="playingRefId === ref.id && ref.youtube_video_id"
                      class="ref-iframe"
                      :src="`https://www.youtube.com/embed/${ref.youtube_video_id}?autoplay=1`"
                      title="YouTube"
                      frameborder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowfullscreen
                    />
                    <button v-else type="button" class="ref-thumb" @click.stop="playRef(ref.id)">
                      <img
                        :src="ref.thumbnail_url || `https://img.youtube.com/vi/${ref.youtube_video_id}/mqdefault.jpg`"
                        :alt="ref.title"
                      />
                      <span class="play-icon">▶</span>
                    </button>
                  </div>
                  <div class="ref-body">
                    <a :href="ref.youtube_url" target="_blank" class="ref-title" @click.stop>{{ ref.title }}</a>
                    <div class="ref-meta">
                      <span v-if="ref.key" class="key-badge sm">{{ ref.key }}</span>
                      <span :class="['trust', ref.trust_level.toLowerCase()]">{{ ref.trust_level }}</span>
                    </div>
                    <div v-if="(detailSong.sheets || []).filter((s: any) => s.reference_id === ref.id).length > 0" class="ref-sheets">
                      <div v-for="sh in (detailSong.sheets || []).filter((s: any) => s.reference_id === ref.id)" :key="sh.id" class="sheet-item">
                        <a :href="sh.file_url" target="_blank">{{ sh.file_type }} 악보</a>
                        <button class="btn-xs danger" @click="deleteSheet(sh.id)">x</button>
                      </div>
                    </div>
                  </div>
                  <button class="btn-xs danger" @click="deleteReference(ref.id)">삭제</button>
                </div>
              </div>

              <!-- 기본 악보 -->
              <div v-if="(detailSong.sheets || []).filter((s: any) => !s.reference_id).length > 0" class="detail-section">
                <div class="detail-section-title">기본 악보</div>
                <div v-for="sh in (detailSong.sheets || []).filter((s: any) => !s.reference_id)" :key="sh.id" class="sheet-item">
                  <a :href="sh.file_url" target="_blank">{{ sh.file_type }} 악보</a>
                  <button class="btn-xs danger" @click="deleteSheet(sh.id)">x</button>
                </div>
              </div>

              <!-- 가사 -->
              <div v-if="detailSong.lyrics" class="detail-section">
                <div class="detail-section-title">가사 / 송폼</div>
                <pre class="lyrics">{{ detailSong.lyrics }}</pre>
              </div>
            </template>
          </template>
        </div>
      </div>
    </Teleport>

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

.card-actions { display: flex; gap: 6px; flex-shrink: 0; }

/* 빠른 편집 모달 */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  padding: 20px;
}
.modal-panel {
  @include card;
  background: var(--bg);
  width: 100%; max-width: 520px;
  max-height: 85vh; overflow-y: auto;
  display: flex; flex-direction: column; gap: 8px;
  padding: 20px;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 4px;
  h3 { margin: 0; font-size: 16px; font-weight: 700; }
}
.field-label {
  font-size: 12px; font-weight: 600; color: var(--text-dim); margin-top: 6px;
}
.key-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.key-chip {
  padding: 4px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: rgba(255,255,255,0.02); color: var(--text-dim);
  font-size: 13px; font-weight: 600; cursor: pointer;
  &.selected { background: var(--accent); border-color: var(--accent); color: #fff; }
}
.tempo-row { display: flex; gap: 8px; }
.lyrics-toggle {
  background: none; border: none; color: var(--text-dim); font-size: 12px;
  cursor: pointer; padding: 4px 0; text-align: left; margin-top: 4px;
  &:hover { color: var(--accent); }
}
.textarea {
  @include input;
  height: auto; padding: 12px 14px;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px; line-height: 1.7;
}
.modal-actions {
  display: flex; gap: 8px; margin-top: 12px;
  .btn { @include btn; }
}

.detail-panel { max-width: 960px; max-height: 92vh; }
.header-actions { display: flex; gap: 6px; }
.detail-loading { padding: 40px; text-align: center; color: var(--text-dim); }
.detail-edit { display: flex; flex-direction: column; gap: 8px; }

.detail-section {
  padding: 12px 0;
  border-top: 1px solid var(--line);
  &:first-of-type { border-top: none; padding-top: 4px; }
}
.detail-section-title {
  font-size: 13px; font-weight: 700; color: var(--text-dim);
  margin-bottom: 8px;
  display: flex; justify-content: space-between; align-items: center;
}

.key-inline { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.key-badge {
  background: var(--accent-soft); color: var(--accent);
  padding: 3px 10px; border-radius: 6px;
  font-size: 13px; font-weight: 700;
  &.sm { font-size: 11px; padding: 1px 6px; }
  &.dim { opacity: 0.5; }
  &.removable {
    cursor: pointer;
    &:hover { background: var(--red-soft); color: var(--red); }
  }
}

.add-ref-form {
  display: flex; flex-direction: column; gap: 6px;
  padding: 10px; margin-bottom: 10px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.ref-sub { display: flex; gap: 6px; }
.input-sm { max-width: 70px; }

.ref-card {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
  &:last-child { border-bottom: none; }
}
.ref-media {
  flex-shrink: 0;
  width: 280px;
  aspect-ratio: 16/9;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
}
.ref-thumb {
  position: relative;
  width: 100%; height: 100%;
  border: none; padding: 0; cursor: pointer;
  display: block; background: #000;
  img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .play-icon {
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    background: rgba(0,0,0,0.35); color: #fff; font-size: 36px;
    transition: background .15s;
  }
  &:hover .play-icon { background: rgba(0,0,0,0.55); }
}
.ref-iframe { width: 100%; height: 100%; border: 0; display: block; }

@media (max-width: 720px) {
  .ref-media { width: 100%; }
  .ref-card { flex-direction: column; }
}
.ref-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.ref-title {
  font-weight: 600; font-size: 13px; color: var(--green);
  word-break: break-word; text-decoration: none;
  &:hover { text-decoration: underline; }
}
.ref-meta { display: flex; gap: 6px; font-size: 12px; color: var(--text-dim); flex-wrap: wrap; }
.trust {
  padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;
  &.high { background: var(--green-soft); color: var(--green); }
  &.medium { background: var(--accent-soft); color: var(--accent); }
  &.low { background: var(--red-soft); color: var(--red); }
}
.ref-sheets { padding-left: 8px; border-left: 2px solid var(--line); margin-top: 4px; }

.sheet-item {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 0; font-size: 12px;
  a { color: var(--accent); &:hover { text-decoration: underline; } }
}

.btn-xs {
  padding: 2px 6px; border-radius: 4px; border: 1px solid var(--line);
  background: transparent; color: var(--text-dim); font-size: 10px; cursor: pointer;
  &.danger { color: var(--red); &:hover { background: var(--red-soft); } }
}
.empty-sm { font-size: 12px; color: var(--text-dim); padding: 8px 0; }

.lyrics {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.7;
  font-family: inherit;
  margin: 0;
}

.song-card { cursor: pointer; }

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
