<script setup lang="ts">
definePageMeta({ layout: 'share' })

const route = useRoute()
const { api } = useApi()

const conti = ref<any>(null)
const loading = ref(true)
const error = ref('')

function displayKey(useKey: string | null): string {
  if (!useKey) return ''
  return useKey.split('-').join(' → ')
}

async function load() {
  try {
    loading.value = true
    conti.value = await api<any>(`/api/contis/${route.params.id}`)
  } catch {
    error.value = '콘티를 불러올 수 없습니다.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="share-page">
    <div v-if="loading" class="loading">불러오는 중...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else-if="conti">
      <div class="share-header">
        <h1>{{ conti.service_name }}</h1>
        <p class="meta">{{ conti.date }} · {{ conti.author }}</p>
      </div>

      <!-- 사역팀 -->
      <section v-if="(conti.members || []).length > 0" class="share-section">
        <h2>사역팀</h2>
        <div class="member-list">
          <div v-for="cm in conti.members" :key="cm.id" class="member-item">
            <span class="position">{{ cm.position }}</span>
            <span class="name">{{ cm.name }}</span>
          </div>
        </div>
      </section>

      <!-- 곡 순서 -->
      <section class="share-section">
        <h2>곡 순서</h2>
        <div class="song-list">
          <div v-for="item in conti.items" :key="item.id" class="song-item">
            <span class="order">{{ item.slot_label || item.order_num }}</span>
            <span class="title">{{ item.song?.title }}</span>
            <span v-if="item.use_key" class="key">{{ displayKey(item.use_key) }}</span>
          </div>
        </div>
      </section>

      <!-- 레퍼런스 -->
      <section v-if="conti.items.some((i: any) => i.reference)" class="share-section">
        <h2>레퍼런스</h2>
        <div class="ref-list">
          <template v-for="item in conti.items" :key="item.id">
            <a
              v-if="item.reference"
              :href="item.reference.youtube_url"
              target="_blank"
              class="ref-item"
            >
              {{ item.song?.title }} - {{ item.reference.title }}
            </a>
          </template>
        </div>
      </section>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

.share-page {
  padding-bottom: 40px;
}

.share-header {
  margin-bottom: 24px;
  h1 { font-size: 22px; font-weight: 800; margin: 0 0 4px; }
  .meta { font-size: 14px; color: var(--text-dim); margin: 0; }
}

.share-section {
  margin-bottom: 24px;

  h2 {
    font-size: 15px;
    font-weight: 700;
    color: var(--accent);
    margin: 0 0 10px;
  }
}

.member-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 8px;
  background: var(--card);
  border: 1px solid var(--line);
  font-size: 13px;

  .position { color: var(--accent); font-weight: 700; font-size: 12px; }
  .name { font-weight: 600; }
}

.song-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.song-item {
  @include card;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;

  .order {
    min-width: 50px;
    font-size: 13px;
    font-weight: 700;
    color: var(--accent);
  }
  .title { font-weight: 600; flex: 1; }
  .key {
    background: var(--accent-soft);
    color: var(--accent);
    padding: 2px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
  }
}

.ref-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ref-item {
  display: block;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--green);
  &:hover { background: rgba(255,255,255,0.05); text-decoration: underline; }
}

.loading, .error {
  text-align: center;
  padding: 40px;
  color: var(--text-dim);
}

.error { color: var(--red); }
</style>
