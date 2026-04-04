<script setup lang="ts">
const route = useRoute()
const { api } = useApi()

const song = ref<any>(null)
const loading = ref(true)

async function load() {
  loading.value = true
  song.value = await api<any>(`/api/songs/${route.params.id}`)
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div v-if="loading" class="loading">불러오는 중...</div>

    <template v-else-if="song">
      <h1>{{ song.title }}</h1>
      <p v-if="song.artist" class="artist">{{ song.artist }}</p>

      <div class="info-row">
        <span v-if="song.default_key" class="key-badge">기본 키: {{ song.default_key }}</span>
      </div>

      <!-- 레퍼런스 -->
      <section class="section">
        <h2>레퍼런스 ({{ song.references.length }})</h2>
        <div v-if="song.references.length === 0" class="empty">레퍼런스 없음</div>
        <div v-for="ref in song.references" :key="ref.id" class="ref-card">
          <a :href="ref.youtube_url" target="_blank" class="ref-title">{{ ref.title }}</a>
          <div class="ref-meta">
            <span v-if="ref.key" class="key-badge">{{ ref.key }}</span>
            <span class="trust" :class="ref.trust_level.toLowerCase()">{{ ref.trust_level }}</span>
            <span class="source">{{ ref.source }}</span>
          </div>
        </div>
      </section>

      <!-- 가사 -->
      <section v-if="song.lyrics" class="section">
        <h2>가사</h2>
        <pre class="lyrics">{{ song.lyrics }}</pre>
      </section>

      <!-- 악보 -->
      <section class="section">
        <h2>악보 ({{ song.sheets.length }})</h2>
        <div v-if="song.sheets.length === 0" class="empty">악보 없음</div>
        <div v-for="sh in song.sheets" :key="sh.id" class="sheet-card">
          <a :href="sh.file_url" target="_blank">{{ sh.file_type }} 악보</a>
          <span v-if="sh.uploaded_by" class="uploader">{{ sh.uploaded_by }}</span>
        </div>
      </section>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

h1 { font-size: 28px; font-weight: 800; margin-bottom: 4px; }
.artist { font-size: 16px; color: var(--text-dim); margin: 0 0 12px; }

.info-row { margin-bottom: 24px; }

.key-badge {
  background: var(--accent-soft);
  color: var(--accent);
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
}

.section {
  margin-bottom: 28px;

  h2 {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 12px;
  }
}

.ref-card {
  @include card;
  padding: 12px 16px;
  margin-bottom: 8px;
}

.ref-title {
  font-weight: 600;
  color: var(--green);
  &:hover { text-decoration: underline; }
}

.ref-meta {
  display: flex;
  gap: 10px;
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-dim);
}

.trust {
  padding: 1px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  &.high { background: var(--green-soft); color: var(--green); }
  &.medium { background: var(--accent-soft); color: var(--accent); }
  &.low { background: var(--red-soft); color: var(--red); }
}

.lyrics {
  @include card;
  padding: 16px;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.8;
}

.sheet-card {
  @include card;
  padding: 12px 16px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;

  a { color: var(--accent); &:hover { text-decoration: underline; } }
  .uploader { font-size: 13px; color: var(--text-dim); }
}

.empty, .loading {
  text-align: center;
  padding: 20px;
  color: var(--text-dim);
}
</style>
