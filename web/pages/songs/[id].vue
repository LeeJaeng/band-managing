<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const { api } = useApi()

const song = ref<any>(null)
const loading = ref(true)
const editing = ref(false)

// 편집 폼
const editForm = ref({ title: '', keys: [] as string[], lyrics: '' })

// 키 목록 (자주 쓰는 키 우선)
const COMMON_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'Bb', 'B']
const OTHER_MAJOR_KEYS = ['C#', 'Db', 'D#', 'Eb', 'F#', 'Gb', 'G#', 'Ab', 'A#']
const MINOR_KEYS = ['Am', 'Bm', 'Cm', 'C#m', 'Dm', 'D#m', 'Ebm', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'A#m', 'Bbm']
const ALL_KEYS = [...COMMON_KEYS, ...OTHER_MAJOR_KEYS, ...MINOR_KEYS]

// 인라인 키 편집
const showKeyPicker = ref(false)
const showAllKeys = ref(false)

// 레퍼런스 추가
const showAddRef = ref(false)
const newRef = ref({ youtube_url: '', title: '', key: '' })

async function load() {
  loading.value = true
  song.value = await api<any>(`/api/songs/${route.params.id}?_t=${Date.now()}`)
  loading.value = false
}

function startEdit() {
  editForm.value = {
    title: song.value.title,
    keys: [...(song.value.keys || [])],
    lyrics: song.value.lyrics || '',
  }
  editing.value = true
}

function toggleKey(key: string) {
  const idx = editForm.value.keys.indexOf(key)
  if (idx >= 0) {
    editForm.value.keys.splice(idx, 1)
  } else {
    editForm.value.keys.push(key)
  }
}

// 인라인 키 추가/제거 (편집 모드 없이)
async function toggleKeyInline(key: string) {
  const currentKeys = [...(song.value.keys || [])]
  const idx = currentKeys.indexOf(key)
  if (idx >= 0) {
    currentKeys.splice(idx, 1)
  } else {
    currentKeys.push(key)
  }
  try {
    await api(`/api/songs/${route.params.id}`, {
      method: 'PUT',
      body: JSON.stringify({ title: song.value.title, keys: currentKeys }),
    })
    await load()
  } catch (e: any) { alert(e.message || '키 저장 실패') }
}

async function saveEdit() {
  try {
    await api(`/api/songs/${route.params.id}`, {
      method: 'PUT',
      body: JSON.stringify(editForm.value),
    })
    editing.value = false
    await load()
  } catch (e: any) { alert(e.message || '저장 실패') }
}

function extractVideoId(url: string): string {
  const match = url.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
  return match ? match[1] : ''
}

async function addReference() {
  if (!newRef.value.youtube_url) return
  const videoId = extractVideoId(newRef.value.youtube_url)
  if (!videoId) { alert('유효한 유튜브 URL을 입력해주세요.'); return }

  try {
    await api(`/api/songs/${route.params.id}/references`, {
      method: 'POST',
      body: JSON.stringify({
        youtube_url: newRef.value.youtube_url,
        youtube_video_id: videoId,
        title: newRef.value.title || song.value.title,
        key: newRef.value.key || null,
        source: 'MANUAL',
        trust_level: 'HIGH',
      }),
    })
    newRef.value = { youtube_url: '', title: '', key: '' }
    showAddRef.value = false
    await load()
  } catch (e: any) { alert(e.message || '추가 실패') }
}

async function deleteReference(refId: string) {
  if (!confirm('레퍼런스를 삭제하시겠습니까?')) return
  try {
    await api(`/api/songs/references/${refId}`, { method: 'DELETE' })
    await load()
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

async function deleteSheet(sheetId: string) {
  if (!confirm('악보를 삭제하시겠습니까?')) return
  try {
    await api(`/api/songs/sheets/${sheetId}`, { method: 'DELETE' })
    await load()
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

async function deleteSong() {
  if (!confirm(`"${song.value.title}" 곡을 삭제하시겠습니까?`)) return
  try {
    await api(`/api/songs/${route.params.id}`, { method: 'DELETE' })
    router.push('/songs')
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div v-if="loading" class="loading">불러오는 중...</div>

    <template v-else-if="song">
      <!-- 헤더 -->
      <div class="song-header">
        <div>
          <h1>{{ song.title }}</h1>
        </div>
        <div class="header-actions">
          <button class="btn" @click="startEdit" v-if="!editing">편집</button>
          <button class="btn-sm danger" @click="deleteSong">삭제</button>
        </div>
      </div>

      <!-- 편집 모드 -->
      <div v-if="editing" class="edit-card">
        <h3>곡 정보 편집</h3>

        <label>곡 제목</label>
        <input v-model="editForm.title" class="input" />

        <label>키 (복수 선택 가능)</label>
        <div class="key-picker">
          <div class="key-picker-group">
            <span class="key-group-label">자주 쓰는 키</span>
            <div class="key-picker-chips">
              <button v-for="k in COMMON_KEYS" :key="k" :class="['key-chip', { selected: editForm.keys.includes(k) }]" @click="toggleKey(k)">{{ k }}</button>
            </div>
          </div>
          <div class="key-picker-group">
            <span class="key-group-label">기타 메이저</span>
            <div class="key-picker-chips">
              <button v-for="k in OTHER_MAJOR_KEYS" :key="k" :class="['key-chip', { selected: editForm.keys.includes(k) }]" @click="toggleKey(k)">{{ k }}</button>
            </div>
          </div>
          <div class="key-picker-group">
            <span class="key-group-label">마이너</span>
            <div class="key-picker-chips">
              <button v-for="k in MINOR_KEYS" :key="k" :class="['key-chip', { selected: editForm.keys.includes(k) }]" @click="toggleKey(k)">{{ k }}</button>
            </div>
          </div>
        </div>

        <label>가사 (송폼)</label>
        <textarea v-model="editForm.lyrics" class="textarea" rows="10" placeholder="[Verse 1]&#10;가사를 입력하세요...&#10;&#10;[Chorus]&#10;후렴 가사..." />

        <div class="form-actions">
          <button class="btn-accent" @click="saveEdit">저장</button>
          <button class="btn" @click="editing = false">취소</button>
        </div>
      </div>

      <!-- 키 (인라인 편집) -->
      <section v-if="!editing" class="section">
        <div class="section-header">
          <h2>키</h2>
        </div>
        <div class="key-inline">
          <span v-for="k in (song.keys || [])" :key="k" class="key-badge removable" @click="toggleKeyInline(k)">{{ k }} ×</span>
          <span v-if="song.default_key && !(song.keys || []).includes(song.default_key)" class="key-badge dim">{{ song.default_key }}</span>
          <button class="key-add-btn" @click="showKeyPicker = !showKeyPicker">+</button>
        </div>
        <div v-if="showKeyPicker" class="key-picker">
          <div class="key-picker-group">
            <span class="key-group-label">자주 쓰는 키</span>
            <div class="key-picker-chips">
              <button
                v-for="k in COMMON_KEYS" :key="k"
                :class="['key-chip', { selected: (song.keys || []).includes(k) }]"
                @click="toggleKeyInline(k)"
              >{{ k }}</button>
            </div>
          </div>
          <div v-if="showAllKeys" class="key-picker-group">
            <span class="key-group-label">기타 메이저</span>
            <div class="key-picker-chips">
              <button
                v-for="k in OTHER_MAJOR_KEYS" :key="k"
                :class="['key-chip', { selected: (song.keys || []).includes(k) }]"
                @click="toggleKeyInline(k)"
              >{{ k }}</button>
            </div>
          </div>
          <div v-if="showAllKeys" class="key-picker-group">
            <span class="key-group-label">마이너</span>
            <div class="key-picker-chips">
              <button
                v-for="k in MINOR_KEYS" :key="k"
                :class="['key-chip', { selected: (song.keys || []).includes(k) }]"
                @click="toggleKeyInline(k)"
              >{{ k }}</button>
            </div>
          </div>
          <button class="key-more-btn" @click="showAllKeys = !showAllKeys">
            {{ showAllKeys ? '접기' : '더보기 (기타 키)' }}
          </button>
        </div>
      </section>

      <!-- 레퍼런스 -->
      <section v-if="!editing" class="section">
        <div class="section-header">
          <h2>레퍼런스 ({{ song.references.length }})</h2>
          <button class="btn-sm" @click="showAddRef = !showAddRef">+ 추가</button>
        </div>

        <div v-if="showAddRef" class="add-form">
          <input v-model="newRef.youtube_url" class="input" placeholder="유튜브 URL" />
          <div class="ref-sub">
            <input v-model="newRef.title" class="input" placeholder="제목 (비우면 곡 제목)" />
            <input v-model="newRef.key" class="input input-sm" placeholder="키" />
          </div>
          <button class="btn-accent" @click="addReference">추가</button>
        </div>

        <div v-if="song.references.length === 0" class="empty-sm">레퍼런스 없음</div>
        <div v-for="ref in song.references" :key="ref.id" class="ref-card">
          <div class="ref-main">
            <a :href="ref.youtube_url" target="_blank" class="ref-title">{{ ref.title }}</a>
            <div class="ref-meta">
              <span v-if="ref.key" class="key-badge sm">{{ ref.key }}</span>
              <span :class="['trust', ref.trust_level.toLowerCase()]">{{ ref.trust_level }}</span>
              <span class="source">{{ ref.source }}</span>
            </div>
          </div>

          <!-- 해당 레퍼런스의 악보 -->
          <div v-if="song.sheets.filter((s: any) => s.reference_id === ref.id).length > 0" class="ref-sheets">
            <div v-for="sh in song.sheets.filter((s: any) => s.reference_id === ref.id)" :key="sh.id" class="sheet-item">
              <a :href="sh.file_url" target="_blank">{{ sh.file_type }} 악보</a>
              <button class="btn-xs danger" @click="deleteSheet(sh.id)">x</button>
            </div>
          </div>

          <button class="btn-xs danger" @click="deleteReference(ref.id)">삭제</button>
        </div>
      </section>

      <!-- 악보 (레퍼런스 미연결) -->
      <section v-if="!editing && song.sheets.filter((s: any) => !s.reference_id).length > 0" class="section">
        <h2>기본 악보</h2>
        <div v-for="sh in song.sheets.filter((s: any) => !s.reference_id)" :key="sh.id" class="sheet-card">
          <a :href="sh.file_url" target="_blank">{{ sh.file_type }} 악보</a>
          <span v-if="sh.uploaded_by" class="uploader">{{ sh.uploaded_by }}</span>
          <button class="btn-xs danger" @click="deleteSheet(sh.id)">x</button>
        </div>
      </section>

      <!-- 가사 -->
      <section v-if="!editing && song.lyrics" class="section">
        <h2>가사 / 송폼</h2>
        <pre class="lyrics">{{ song.lyrics }}</pre>
      </section>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

.song-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 12px;

  h1 { font-size: 24px; font-weight: 800; margin: 0 0 4px; }
}

.header-actions { display: flex; gap: 8px; flex-shrink: 0; }

.btn { @include btn; }
.btn-accent { @include btn-accent; }
.input { @include input; }

.edit-card {
  @include card;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 24px;

  h3 { margin: 0 0 4px; font-size: 16px; }
  label { font-size: 13px; font-weight: 600; color: var(--text-dim); margin-top: 4px; }
}

.key-chip {
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.02);
  color: var(--text-dim);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;

  &.selected {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }

  &:hover:not(.selected) { background: rgba(255,255,255,0.05); }
}

.textarea {
  @include input;
  height: auto;
  padding: 12px 14px;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.7;
}

.form-actions { display: flex; gap: 8px; margin-top: 8px; }

.section {
  margin-bottom: 24px;
  h2 { font-size: 17px; font-weight: 700; margin-bottom: 10px; }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  h2 { margin: 0; }
}

.key-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.key-badge {
  background: var(--accent-soft);
  color: var(--accent);
  padding: 3px 12px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;

  &.sm { font-size: 12px; padding: 1px 8px; }
  &.dim { opacity: 0.5; }
  &.removable {
    cursor: pointer;
    &:hover { background: var(--red-soft); color: var(--red); }
  }
}

.key-add-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px dashed var(--text-dim);
  background: transparent;
  color: var(--text-dim);
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  &:hover { border-color: var(--accent); color: var(--accent); }
}

.key-picker {
  @include card;
  padding: 14px;
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.key-picker-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.key-group-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
}

.key-picker-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.key-more-btn {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 0;
  text-align: left;
  &:hover { color: var(--accent); }
}

.add-form {
  @include card;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.ref-sub {
  display: flex;
  gap: 8px;
}

.input-sm { max-width: 80px; }

.ref-card {
  @include card;
  padding: 12px 16px;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ref-main { flex: 1; }

.ref-title {
  font-weight: 600;
  color: var(--green);
  word-break: break-word;
  &:hover { text-decoration: underline; }
}

.ref-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-dim);
  flex-wrap: wrap;
}

.trust {
  padding: 1px 8px; border-radius: 6px; font-size: 12px; font-weight: 700;
  &.high { background: var(--green-soft); color: var(--green); }
  &.medium { background: var(--accent-soft); color: var(--accent); }
  &.low { background: var(--red-soft); color: var(--red); }
}

.ref-sheets {
  padding-left: 12px;
  border-left: 2px solid var(--line);
}

.sheet-item, .sheet-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  font-size: 13px;

  a { color: var(--accent); &:hover { text-decoration: underline; } }
  .uploader { color: var(--text-dim); }
}

.sheet-card {
  @include card;
  padding: 10px 14px;
  margin-bottom: 6px;
}

.lyrics {
  @include card;
  padding: 16px;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.8;
  font-family: inherit;
}

.btn-sm {
  padding: 4px 14px; border-radius: 8px; border: 1px solid var(--line);
  background: rgba(255,255,255,0.02); color: var(--accent); font-size: 13px;
  font-weight: 700; cursor: pointer;
  &:hover { background: var(--accent-soft); }
  &.danger { color: var(--red); &:hover { background: var(--red-soft); } }
}

.btn-xs {
  padding: 2px 8px; border-radius: 6px; border: 1px solid var(--line);
  background: transparent; color: var(--text-dim); font-size: 11px; cursor: pointer;
  &.danger { color: var(--red); &:hover { background: var(--red-soft); } }
}

.loading, .empty-sm {
  text-align: center;
  padding: 16px;
  color: var(--text-dim);
  font-size: 14px;
}

@media (max-width: 640px) {
  .ref-sub { flex-direction: column; }
  .input-sm { max-width: 100%; }
  .song-header { flex-direction: column; }
}
</style>
