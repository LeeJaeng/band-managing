<script setup lang="ts">
const { api } = useApi()

// SSR에서 목록을 미리 로드 — 빈 화면/스턱 로딩 방지
const { data, pending: loading, error: fetchError, refresh } = await useAsyncData(
  'conti-list',
  () => api<any>('/api/contis'),
  { default: () => ({ items: [] }) },
)

const contis = computed<any[]>(() => data.value?.items || [])
const loadError = computed(() => {
  if (!fetchError.value) return ''
  const e: any = fetchError.value
  return e?.data?.detail || e?.message || '콘티 목록을 불러오지 못했습니다.'
})

async function load() { await refresh() }
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>콘티 목록</h1>
      <NuxtLink to="/conti/new" class="btn-accent">새 콘티 만들기</NuxtLink>
    </div>

    <div v-if="loading" class="loading">불러오는 중...</div>

    <div v-else-if="loadError" class="load-error">
      <p>{{ loadError }}</p>
      <button class="btn-retry" @click="load">다시 시도</button>
    </div>

    <div v-else-if="contis.length === 0" class="empty">
      아직 콘티가 없습니다. 첫 콘티를 만들어보세요.
    </div>

    <div v-else class="conti-list">
      <NuxtLink
        v-for="c in contis"
        :key="c.id"
        :to="`/conti/${c.id}`"
        class="conti-card"
      >
        <div class="conti-date">{{ c.date }}</div>
        <div class="conti-name">{{ c.service_name }}</div>
        <div class="conti-meta">
          <span class="conti-author">{{ c.author }}</span>
          <span :class="['conti-status', c.status.toLowerCase()]">{{ c.status === 'CONFIRMED' ? '확정' : '작성중' }}</span>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  h1 { font-size: 24px; font-weight: 800; }
}

.btn-accent { @include btn-accent; }

.loading, .empty {
  text-align: center;
  padding: 60px 0;
  color: var(--text-dim);
}

.load-error {
  @include card;
  padding: 32px 20px;
  text-align: center;
  color: var(--text-dim);

  p { margin: 0 0 16px; font-size: 14px; }
}

.btn-retry {
  @include btn;
  padding: 8px 20px;
}

.conti-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conti-card {
  @include card;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: border-color .15s;

  &:hover { border-color: rgba(139,111,255,0.4); }
}

.conti-date {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
  min-width: 90px;
}

.conti-name {
  flex: 1;
  font-weight: 600;
}

.conti-meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--text-dim);
}

@media (max-width: 640px) {
  .conti-card {
    flex-wrap: wrap;
    gap: 6px;
  }
  .conti-date { min-width: auto; }
  .conti-name { width: 100%; }
}

.conti-status {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;

  &.draft { background: var(--accent-soft); color: var(--accent); }
  &.confirmed { background: var(--green-soft); color: var(--green); }
}
</style>
