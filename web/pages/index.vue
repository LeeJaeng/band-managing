<script setup lang="ts">
const { api } = useApi()

const contis = ref<any[]>([])
const loading = ref(true)

async function load() {
  loading.value = true
  const data = await api<any>('/api/contis')
  contis.value = data.items
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1>콘티 목록</h1>
      <NuxtLink to="/conti/new" class="btn-accent">새 콘티 만들기</NuxtLink>
    </div>

    <div v-if="loading" class="loading">불러오는 중...</div>

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

.conti-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conti-card {
  @include card;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: border-color .15s;

  &:hover { border-color: rgba(124,92,255,0.4); }
}

.conti-date {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
  min-width: 100px;
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

.conti-status {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;

  &.draft { background: var(--accent-soft); color: var(--accent); }
  &.confirmed { background: var(--green-soft); color: var(--green); }
}
</style>
