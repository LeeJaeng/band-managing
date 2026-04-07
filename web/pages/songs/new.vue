<script setup lang="ts">
const router = useRouter()
const { api } = useApi()

const form = ref({
  title: '',
  default_key: '',
  keys: [] as string[],
  lyrics: '',
})

// 키 목록 (자주 쓰는 키 우선)
const COMMON_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'Bb', 'B']
const OTHER_MAJOR_KEYS = ['C#', 'Db', 'D#', 'Eb', 'F#', 'Gb', 'G#', 'Ab', 'A#']
const MINOR_KEYS = ['Am', 'Bm', 'Cm', 'C#m', 'Dm', 'D#m', 'Ebm', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'A#m', 'Bbm']
const showAllKeys = ref(false)

function toggleKey(key: string) {
  const idx = form.value.keys.indexOf(key)
  if (idx >= 0) {
    form.value.keys.splice(idx, 1)
  } else {
    form.value.keys.push(key)
  }
}

const refs = ref<Array<{ youtube_url: string; title: string; key: string }>>([
  { youtube_url: '', title: '', key: '' },
])

const error = ref('')
const saving = ref(false)

function addRef() {
  refs.value.push({ youtube_url: '', title: '', key: '' })
}

function removeRef(idx: number) {
  refs.value.splice(idx, 1)
}

function extractVideoId(url: string): string {
  const match = url.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
  return match ? match[1] : ''
}

async function save() {
  if (!form.value.title.trim()) {
    error.value = '곡 제목을 입력해주세요.'
    return
  }

  saving.value = true
  error.value = ''

  try {
    // 1. 곡 등록
    const song = await api<any>('/api/songs', {
      method: 'POST',
      body: JSON.stringify(form.value),
    })

    // 2. 레퍼런스 추가
    for (const ref of refs.value) {
      if (!ref.youtube_url.trim()) continue
      const videoId = extractVideoId(ref.youtube_url)
      if (!videoId) continue

      await api(`/api/songs/${song.id}/references`, {
        method: 'POST',
        body: JSON.stringify({
          youtube_url: ref.youtube_url,
          youtube_video_id: videoId,
          title: ref.title || form.value.title,
          key: ref.key || null,
          source: 'MANUAL',
          trust_level: 'HIGH',
        }),
      })
    }

    router.push('/songs')
  } catch (e: any) {
    error.value = e.message || '등록 중 오류가 발생했습니다.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1>곡 등록</h1>

    <div class="form-card">
      <div class="form-section">
        <h3>기본 정보</h3>

        <label>곡 제목 *</label>
        <input v-model="form.title" class="input" placeholder="예: 주만 바라볼찌라" />

        <label>키 (복수 선택 가능)</label>
        <div class="key-picker">
          <div class="key-picker-group">
            <span class="key-group-label">자주 쓰는 키</span>
            <div class="key-picker-chips">
              <button
                v-for="k in COMMON_KEYS" :key="k" type="button"
                :class="['key-chip', { selected: form.keys.includes(k) }]"
                @click="toggleKey(k)"
              >{{ k }}</button>
            </div>
          </div>
          <div v-if="showAllKeys" class="key-picker-group">
            <span class="key-group-label">기타 메이저</span>
            <div class="key-picker-chips">
              <button
                v-for="k in OTHER_MAJOR_KEYS" :key="k" type="button"
                :class="['key-chip', { selected: form.keys.includes(k) }]"
                @click="toggleKey(k)"
              >{{ k }}</button>
            </div>
          </div>
          <div v-if="showAllKeys" class="key-picker-group">
            <span class="key-group-label">마이너</span>
            <div class="key-picker-chips">
              <button
                v-for="k in MINOR_KEYS" :key="k" type="button"
                :class="['key-chip', { selected: form.keys.includes(k) }]"
                @click="toggleKey(k)"
              >{{ k }}</button>
            </div>
          </div>
          <button type="button" class="key-more-btn" @click="showAllKeys = !showAllKeys">
            {{ showAllKeys ? '접기' : '더보기 (기타 키)' }}
          </button>
        </div>

        <label>가사</label>
        <textarea v-model="form.lyrics" class="textarea" rows="6" placeholder="가사를 입력하세요..." />
      </div>

      <div class="form-section">
        <div class="section-header">
          <h3>레퍼런스 (유튜브)</h3>
          <button class="btn-sm" @click="addRef">+ 추가</button>
        </div>

        <div v-for="(r, idx) in refs" :key="idx" class="ref-row">
          <div class="ref-fields">
            <input v-model="r.youtube_url" class="input" placeholder="유튜브 URL" />
            <div class="ref-sub">
              <input v-model="r.title" class="input" placeholder="레퍼런스 제목 (비우면 곡 제목)" />
              <input v-model="r.key" class="input input-sm" placeholder="키" />
            </div>
          </div>
          <button v-if="refs.length > 1" class="btn-remove" @click="removeRef(idx)">x</button>
        </div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <button class="btn-accent" :disabled="saving" @click="save">
        {{ saving ? '등록 중...' : '곡 등록' }}
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

h1 { font-size: 24px; font-weight: 800; margin-bottom: 20px; }

.form-card {
  @include card;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 10px;

  h3 {
    font-size: 16px;
    font-weight: 700;
    margin: 0;
  }

  label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-dim);
    margin-top: 4px;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input { @include input; }

.input-sm { max-width: 80px; }

.textarea {
  @include input;
  height: auto;
  padding: 12px 14px;
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
}

.ref-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 12px;
  border-radius: var(--radius);
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--line);
}

.ref-fields {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ref-sub {
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.02);
  color: var(--accent);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  &:hover { background: var(--accent-soft); }
}

.key-picker {
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

.btn-remove {
  @include btn;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
  font-size: 14px;
  color: var(--red);
  flex-shrink: 0;
  margin-top: 6px;
  &:hover { background: var(--red-soft); }
}

.btn-accent { @include btn-accent; }

.error { color: var(--red); font-size: 13px; }

@media (max-width: 640px) {
  .ref-sub { flex-direction: column; }
  .input-sm { max-width: 100%; }
}
</style>
