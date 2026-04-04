<script setup lang="ts">
const { api } = useApi()

const channels = ref<any[]>([])
const logs = ref<any[]>([])
const reviewQueue = ref<any[]>([])
const loading = ref(true)
const crawling = ref(false)

// 채널 등록 폼
const newChannel = ref({ name: '', youtube_channel_url: '', youtube_channel_id: '', trust_level: 'HIGH' })
const showAddChannel = ref(false)

async function load() {
  loading.value = true
  const [ch, lg, rq] = await Promise.all([
    api<any[]>('/api/admin/channels'),
    api<any[]>('/api/admin/crawl/logs?limit=10'),
    api<any[]>('/api/admin/review-queue?status=PENDING'),
  ])
  channels.value = ch
  logs.value = lg
  reviewQueue.value = rq
  loading.value = false
}

async function addChannel() {
  if (!newChannel.value.name || !newChannel.value.youtube_channel_id) return
  await api('/api/admin/channels', { method: 'POST', body: JSON.stringify(newChannel.value) })
  newChannel.value = { name: '', youtube_channel_url: '', youtube_channel_id: '', trust_level: 'HIGH' }
  showAddChannel.value = false
  await load()
}

async function toggleChannel(ch: any) {
  await api(`/api/admin/channels/${ch.id}`, {
    method: 'PUT',
    body: JSON.stringify({ is_active: !ch.is_active }),
  })
  await load()
}

async function deleteChannel(ch: any) {
  await api(`/api/admin/channels/${ch.id}`, { method: 'DELETE' })
  await load()
}

async function crawlChannel(channelId: string) {
  crawling.value = true
  await api(`/api/admin/crawl/${channelId}`, { method: 'POST' })
  crawling.value = false
  await load()
}

async function crawlAll() {
  crawling.value = true
  await api('/api/admin/crawl/all', { method: 'POST' })
  crawling.value = false
  await load()
}

async function approveReview(rq: any) {
  await api(`/api/admin/review/${rq.id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ song_title: rq.parsed_song_title }),
  })
  await load()
}

async function rejectReview(rq: any) {
  await api(`/api/admin/review/${rq.id}/reject`, { method: 'POST' })
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>관리자</h1>

    <div v-if="loading" class="loading">불러오는 중...</div>

    <template v-else>
      <!-- 채널 관리 -->
      <section class="section">
        <div class="section-header">
          <h2>크롤링 채널 ({{ channels.length }})</h2>
          <div class="section-actions">
            <button class="btn" @click="showAddChannel = !showAddChannel">채널 추가</button>
            <button class="btn-accent" :disabled="crawling" @click="crawlAll">
              {{ crawling ? '크롤링 중...' : '전체 크롤링' }}
            </button>
          </div>
        </div>

        <!-- 채널 추가 폼 -->
        <div v-if="showAddChannel" class="add-form">
          <input v-model="newChannel.name" class="input" placeholder="사역팀 이름" />
          <input v-model="newChannel.youtube_channel_url" class="input" placeholder="유튜브 채널 URL" />
          <input v-model="newChannel.youtube_channel_id" class="input" placeholder="유튜브 채널 ID" />
          <select v-model="newChannel.trust_level" class="input">
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
          <button class="btn-accent" @click="addChannel">등록</button>
        </div>

        <div class="channel-list">
          <div v-for="ch in channels" :key="ch.id" class="channel-card">
            <div class="ch-info">
              <span class="ch-name">{{ ch.name }}</span>
              <span :class="['trust', ch.trust_level.toLowerCase()]">{{ ch.trust_level }}</span>
              <span :class="ch.is_active ? 'active' : 'inactive'">
                {{ ch.is_active ? '활성' : '비활성' }}
              </span>
            </div>
            <div class="ch-meta">
              <span v-if="ch.last_crawled_at">마지막: {{ ch.last_crawled_at }}</span>
            </div>
            <div class="ch-actions">
              <button class="btn-sm" @click="crawlChannel(ch.id)" :disabled="crawling">크롤링</button>
              <button class="btn-sm" @click="toggleChannel(ch)">
                {{ ch.is_active ? '비활성화' : '활성화' }}
              </button>
              <button class="btn-sm danger" @click="deleteChannel(ch)">삭제</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 검증 큐 -->
      <section class="section">
        <h2>검증 큐 ({{ reviewQueue.length }})</h2>
        <div v-if="reviewQueue.length === 0" class="empty">대기 중인 항목 없음</div>
        <div v-for="rq in reviewQueue" :key="rq.id" class="review-card">
          <div class="rv-info">
            <div class="rv-title">{{ rq.video_title }}</div>
            <div class="rv-parsed">파싱: {{ rq.parsed_song_title || '(없음)' }}</div>
          </div>
          <div class="rv-actions">
            <button class="btn-sm approve" @click="approveReview(rq)">승인</button>
            <button class="btn-sm danger" @click="rejectReview(rq)">거부</button>
          </div>
        </div>
      </section>

      <!-- 크롤링 로그 -->
      <section class="section">
        <h2>최근 크롤링 로그</h2>
        <div v-if="logs.length === 0" class="empty">로그 없음</div>
        <div v-for="log in logs" :key="log.id" class="log-card">
          <span :class="['log-status', log.status.toLowerCase()]">{{ log.status }}</span>
          <span>영상 {{ log.videos_found }}개</span>
          <span>레퍼런스 +{{ log.refs_added }}</span>
          <span class="log-time">{{ log.started_at }}</span>
          <span v-if="log.error_message" class="log-error">{{ log.error_message }}</span>
        </div>
      </section>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

h1 { font-size: 24px; font-weight: 800; margin-bottom: 24px; }
h2 { font-size: 18px; font-weight: 700; margin-bottom: 12px; }

.btn { @include btn; }
.btn-accent { @include btn-accent; }
.input { @include input; }

.section {
  margin-bottom: 32px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h2 { margin: 0; }
}

.section-actions {
  display: flex;
  gap: 8px;
}

.add-form {
  @include card;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.channel-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.channel-card {
  @include card;
  padding: 14px 16px;
}

.ch-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.ch-name { font-weight: 600; }

.trust {
  padding: 1px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  &.high { background: var(--green-soft); color: var(--green); }
  &.medium { background: var(--accent-soft); color: var(--accent); }
  &.low { background: var(--red-soft); color: var(--red); }
}

.active { color: var(--green); font-size: 12px; }
.inactive { color: var(--red); font-size: 12px; }

.ch-meta { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }

.ch-actions {
  display: flex;
  gap: 6px;
}

.btn-sm {
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.02);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  &:hover { background: rgba(255,255,255,0.05); }
  &.danger { color: var(--red); &:hover { background: var(--red-soft); } }
  &.approve { color: var(--green); &:hover { background: var(--green-soft); } }
  &:disabled { opacity: .5; cursor: not-allowed; }
}

.review-card {
  @include card;
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rv-info { flex: 1; }
.rv-title { font-weight: 600; margin-bottom: 4px; }
.rv-parsed { font-size: 13px; color: var(--text-dim); }

.rv-actions { display: flex; gap: 6px; }

.log-card {
  @include card;
  padding: 10px 14px;
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
}

.log-status {
  padding: 1px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  &.success { background: var(--green-soft); color: var(--green); }
  &.failed { background: var(--red-soft); color: var(--red); }
  &.running { background: var(--accent-soft); color: var(--accent); }
}

.log-time { color: var(--text-dim); }
.log-error { color: var(--red); }

.loading, .empty {
  text-align: center;
  padding: 20px;
  color: var(--text-dim);
}
</style>
