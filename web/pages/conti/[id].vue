<script setup lang="ts">
definePageMeta({})
const route = useRoute()
const { api } = useApi()

const conti = ref<any>(null)
const loading = ref(true)
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const searching = ref(false)

// 키 선택 관련
const COMMON_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'Bb', 'B']
const OTHER_MAJOR_KEYS = ['C#', 'Db', 'D#', 'Eb', 'F#', 'Gb', 'G#', 'Ab', 'A#']
const MINOR_KEYS = ['Am', 'Bm', 'Cm', 'C#m', 'Dm', 'D#m', 'Ebm', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'A#m', 'Bbm']
const editingKeyItemId = ref<string | null>(null)
const keyChain = ref<string[]>([])  // 키업 체인: ["E", "F", "G"]
const showAllKeys = ref(false)

// use_key 표시: "E-F-G" → "E → F → G"
function displayKey(useKey: string | null): string {
  if (!useKey) return ''
  return useKey.split('-').join(' → ')
}

// 키 편집 시작
function startKeyEdit(item: any) {
  editingKeyItemId.value = item.id
  showAllKeys.value = false
  if (item.use_key) {
    keyChain.value = item.use_key.split('-')
  } else {
    keyChain.value = []
  }
}

// 키 체인에 추가/제거
function toggleKeyInChain(key: string) {
  const lastIdx = keyChain.value.lastIndexOf(key)
  // 마지막 키와 같으면 제거, 아니면 추가 (키업이므로 같은 키 중복 가능하지 않게)
  if (keyChain.value.length > 0 && keyChain.value[keyChain.value.length - 1] === key) {
    keyChain.value.pop()
  } else {
    keyChain.value.push(key)
  }
}

// 키 체인 저장
async function saveKeyChain(itemId: string) {
  const useKey = keyChain.value.length > 0 ? keyChain.value.join('-') : null
  await api(`/api/contis/items/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify({ use_key: useKey }),
  })
  editingKeyItemId.value = null
  await load()
}

function cancelKeyEdit() {
  editingKeyItemId.value = null
}

// 사역 멤버 배정
const teamMembers = ref<any[]>([])
const showMemberAdd = ref(false)

async function loadTeamMembers() {
  try {
    const data = await api<any>('/api/team/members?active_only=true')
    teamMembers.value = data.items || []
  } catch { /* 미로그인 시 무시 */ }
}

async function addContiMember(member: any) {
  await api(`/api/contis/${route.params.id}/members`, {
    method: 'POST',
    body: JSON.stringify({ member_id: member.id, position: member.position }),
  })
  showMemberAdd.value = false
  await load()
}

async function removeContiMember(cmId: string) {
  await api(`/api/contis/${route.params.id}/members/${cmId}`, { method: 'DELETE' })
  await load()
}

// 이미 배정된 멤버 필터링
const availableMembers = computed(() => {
  const assignedIds = new Set((conti.value?.members || []).map((m: any) => m.member_id))
  return teamMembers.value.filter(m => !assignedIds.has(m.id))
})

async function load() {
  loading.value = true
  try {
    conti.value = await api<any>(`/api/contis/${route.params.id}`)
  } catch (e: any) {
    console.error('conti load error:', e)
    conti.value = null
  }
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
  // 곡 DB에 키가 있으면 첫 번째 키를 use_key로 선입력
  const defaultKey = song.keys?.[0] || song.default_key || null
  await api('/api/contis/' + route.params.id + '/items', {
    method: 'POST',
    body: JSON.stringify({
      song_id: song.id,
      order_num: nextOrder,
      slot_label: `${nextOrder}번곡`,
      use_key: defaultKey,
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

// 공유 기능
const copied = ref('')

function generateShareText(): string {
  if (!conti.value) return ''
  const c = conti.value
  const lines: string[] = []

  lines.push(`📋 ${c.service_name} 콘티 (${c.date})`)
  lines.push('')

  // 사역팀
  if (c.members && c.members.length > 0) {
    lines.push('🎵 사역팀')
    // 같은 포지션 그룹핑
    const posMap = new Map<string, string[]>()
    for (const m of c.members) {
      const names = posMap.get(m.position) || []
      names.push(m.name)
      posMap.set(m.position, names)
    }
    const parts = Array.from(posMap.entries()).map(([pos, names]) => `${pos}: ${names.join(', ')}`)
    lines.push(parts.join(' | '))
    lines.push('')
  }

  // 곡 순서
  if (c.items && c.items.length > 0) {
    lines.push('🎶 곡 순서')
    for (const item of c.items) {
      const keyStr = item.use_key ? displayKey(item.use_key) : ''
      const parts = [item.slot_label || `${item.order_num}번곡`, item.song?.title || '']
      if (keyStr) parts.push(keyStr)
      lines.push(parts.join(' | '))
    }
    lines.push('')
  }

  // 레퍼런스
  const refsWithUrl = (c.items || []).filter((i: any) => i.reference)
  if (refsWithUrl.length > 0) {
    lines.push('🔗 레퍼런스')
    for (const item of refsWithUrl) {
      lines.push(`${item.song?.title} - ${item.reference.youtube_url}`)
    }
  }

  return lines.join('\n').trim()
}

async function copyShareText() {
  const text = generateShareText()
  await navigator.clipboard.writeText(text)
  copied.value = 'text'
  setTimeout(() => { copied.value = '' }, 2000)
}

async function copyShareLink() {
  const url = `${window.location.origin}/conti/share/${route.params.id}`
  await navigator.clipboard.writeText(url)
  copied.value = 'link'
  setTimeout(() => { copied.value = '' }, 2000)
}

onMounted(() => {
  load()
  loadTeamMembers()
})
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
          <button class="btn-share" @click="copyShareText">
            {{ copied === 'text' ? '복사됨!' : '텍스트 복사' }}
          </button>
          <button class="btn-share" @click="copyShareLink">
            {{ copied === 'link' ? '복사됨!' : '링크 복사' }}
          </button>
          <button v-if="conti.status === 'DRAFT'" class="btn-accent" @click="confirmConti">확정</button>
        </div>
      </div>

      <!-- 사역팀 -->
      <section class="section members-section">
        <div class="section-header-row">
          <h2>사역팀</h2>
          <button class="btn-sm-add" @click="showMemberAdd = !showMemberAdd">+ 배정</button>
        </div>
        <div v-if="(conti.members || []).length > 0" class="member-chips">
          <div v-for="cm in conti.members" :key="cm.id" class="member-chip">
            <span class="chip-position">{{ cm.position }}</span>
            <span class="chip-name">{{ cm.name }}</span>
            <button class="chip-remove" @click="removeContiMember(cm.id)">×</button>
          </div>
        </div>
        <div v-else class="empty-sm">배정된 팀원 없음</div>

        <div v-if="showMemberAdd && availableMembers.length > 0" class="member-add-list">
          <div
            v-for="m in availableMembers" :key="m.id"
            class="member-add-item"
            @click="addContiMember(m)"
          >
            <span class="add-name">{{ m.name }}</span>
            <span class="add-position">{{ m.position }}</span>
          </div>
        </div>
        <div v-if="showMemberAdd && availableMembers.length === 0" class="empty-sm">
          배정 가능한 팀원 없음
        </div>
      </section>

      <!-- 곡 목록 -->
      <div class="items">
        <div v-for="item in conti.items" :key="item.id" class="item-card">
          <div class="item-order">{{ item.slot_label || item.order_num }}</div>
          <div class="item-info">
            <div class="item-title">{{ item.song?.title }}</div>
            <div class="item-detail">
              <!-- 키 표시 (클릭하면 편집) -->
              <span
                v-if="editingKeyItemId !== item.id && (item.use_key || item.song?.default_key)"
                class="key-badge clickable"
                @click="startKeyEdit(item)"
              >
                {{ displayKey(item.use_key) || item.song?.default_key }}
              </span>
              <button
                v-if="editingKeyItemId !== item.id && !item.use_key && !item.song?.default_key"
                class="key-add-btn-sm"
                @click="startKeyEdit(item)"
              >키 설정</button>
              <span v-if="item.reference" class="ref-link">
                <a :href="item.reference.youtube_url" target="_blank">{{ item.reference.title }}</a>
              </span>
              <span v-if="item.memo" class="memo">{{ item.memo }}</span>
            </div>

            <!-- 인라인 키 편집 -->
            <div v-if="editingKeyItemId === item.id" class="key-edit-inline">
              <div class="key-chain-preview">
                <template v-if="keyChain.length > 0">
                  <span v-for="(k, idx) in keyChain" :key="idx" class="key-chain-item">
                    <span v-if="idx > 0" class="key-arrow">→</span>
                    <span class="key-badge active">{{ k }}</span>
                  </span>
                </template>
                <span v-else class="key-chain-empty">키를 선택하세요</span>
              </div>
              <div class="key-picker-compact">
                <div class="key-picker-chips">
                  <button
                    v-for="k in COMMON_KEYS" :key="k"
                    :class="['key-chip', { selected: keyChain.includes(k) }]"
                    @click="toggleKeyInChain(k)"
                  >{{ k }}</button>
                </div>
                <div v-if="showAllKeys" class="key-picker-chips">
                  <button
                    v-for="k in OTHER_MAJOR_KEYS" :key="k"
                    :class="['key-chip', { selected: keyChain.includes(k) }]"
                    @click="toggleKeyInChain(k)"
                  >{{ k }}</button>
                </div>
                <div v-if="showAllKeys" class="key-picker-chips">
                  <button
                    v-for="k in MINOR_KEYS" :key="k"
                    :class="['key-chip', { selected: keyChain.includes(k) }]"
                    @click="toggleKeyInChain(k)"
                  >{{ k }}</button>
                </div>
                <div class="key-edit-actions">
                  <button class="key-more-btn" @click="showAllKeys = !showAllKeys">
                    {{ showAllKeys ? '접기' : '더보기' }}
                  </button>
                  <div class="key-edit-btns">
                    <button class="btn-save-sm" @click="saveKeyChain(item.id)">저장</button>
                    <button class="btn-cancel-sm" @click="cancelKeyEdit">취소</button>
                  </div>
                </div>
              </div>
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
            <span v-if="(song.keys || []).length > 0" class="key-badges">
              <span v-for="k in song.keys" :key="k" class="key-badge">{{ k }}</span>
            </span>
            <span v-else-if="song.default_key" class="key-badge">{{ song.default_key }}</span>
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
.btn-share {
  @include btn;
  font-size: 12px;
  padding: 6px 12px;
  color: var(--accent);
  border-color: var(--accent);
  &:hover { background: var(--accent-soft); }
}
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

  &.clickable {
    cursor: pointer;
    &:hover { background: var(--accent); color: #fff; }
  }

  &.active {
    background: var(--accent);
    color: #fff;
  }
}

.key-badges {
  display: flex;
  gap: 4px;
}

.key-add-btn-sm {
  background: none;
  border: 1px dashed var(--text-dim);
  color: var(--text-dim);
  padding: 1px 8px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  &:hover { border-color: var(--accent); color: var(--accent); }
}

.key-edit-inline {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.key-chain-preview {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
}

.key-chain-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.key-arrow {
  color: var(--text-dim);
  font-size: 12px;
  font-weight: 700;
}

.key-chain-empty {
  color: var(--text-dim);
  font-size: 12px;
}

.key-picker-compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.key-picker-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.key-chip {
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.02);
  color: var(--text-dim);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;

  &.selected {
    background: var(--accent-soft);
    border-color: var(--accent);
    color: var(--accent);
  }

  &:hover:not(.selected) { background: rgba(255,255,255,0.05); }
}

.key-edit-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.key-more-btn {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 11px;
  cursor: pointer;
  padding: 0;
  &:hover { color: var(--accent); }
}

.key-edit-btns {
  display: flex;
  gap: 6px;
}

.btn-save-sm {
  padding: 3px 12px;
  border-radius: 6px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  &:hover { opacity: 0.9; }
}

.btn-cancel-sm {
  padding: 3px 12px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--text-dim);
  font-size: 12px;
  cursor: pointer;
  &:hover { background: rgba(255,255,255,0.05); }
}

.members-section { margin-bottom: 24px; }

.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  h2 { font-size: 16px; font-weight: 700; margin: 0; }
}

.btn-sm-add {
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.02);
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  &:hover { background: var(--accent-soft); }
}

.member-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.member-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 8px;
  background: var(--card);
  border: 1px solid var(--line);
  font-size: 13px;
}

.chip-position {
  color: var(--accent);
  font-weight: 700;
  font-size: 12px;
}

.chip-name { font-weight: 600; }

.chip-remove {
  background: none;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 14px;
  padding: 0 2px;
  &:hover { color: var(--red); }
}

.member-add-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.member-add-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  &:hover { background: rgba(255,255,255,0.05); }
}

.add-name { font-weight: 600; }
.add-position { color: var(--text-dim); font-size: 12px; }

.empty-sm {
  color: var(--text-dim);
  font-size: 13px;
  padding: 8px 0;
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
