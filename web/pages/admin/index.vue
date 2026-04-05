<script setup lang="ts">
definePageMeta({ middleware: 'admin' })
const { api } = useApi()

const channels = ref<any[]>([])
const logs = ref<any[]>([])
const reviewQueue = ref<any[]>([])
const members = ref<any[]>([])
const userSongs = ref<any[]>([])
const loading = ref(true)
const crawling = ref(false)

// 팀원 관리
const POSITIONS = ['피아노', '신디', '드럼', '베이스', '보컬', '기타', '어쿠스틱', '기타(일렉)']
const showMemberForm = ref(false)
const editingMemberId = ref<string | null>(null)
const memberForm = ref({ name: '', position: '보컬' })

function openMemberAdd() {
  editingMemberId.value = null
  memberForm.value = { name: '', position: '보컬' }
  showMemberForm.value = true
}

function openMemberEdit(m: any) {
  editingMemberId.value = m.id
  memberForm.value = { name: m.name, position: m.position }
  showMemberForm.value = true
}

async function saveMember() {
  if (!memberForm.value.name.trim()) { alert('이름을 입력해주세요.'); return }
  try {
    if (editingMemberId.value) {
      await api(`/api/team/members/${editingMemberId.value}`, {
        method: 'PUT',
        body: JSON.stringify(memberForm.value),
      })
    } else {
      await api('/api/team/members', {
        method: 'POST',
        body: JSON.stringify(memberForm.value),
      })
    }
    showMemberForm.value = false
    editingMemberId.value = null
    await load()
  } catch (e: any) { alert(e.message || '저장 실패') }
}

async function toggleMember(m: any) {
  try {
    await api(`/api/team/members/${m.id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: !m.is_active }),
    })
    await load()
  } catch (e: any) { alert(e.message || '수정 실패') }
}

async function deleteMember(m: any) {
  if (!confirm(`"${m.name}" 팀원을 삭제하시겠습니까?`)) return
  try {
    await api(`/api/team/members/${m.id}`, { method: 'DELETE' })
    await load()
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

// 채널 등록/편집
const showChannelForm = ref(false)
const editingChannelId = ref<string | null>(null)
const channelForm = ref({ name: '', youtube_channel_url: '', youtube_channel_id: '', trust_level: 'HIGH' })
const resolving = ref(false)

async function load() {
  loading.value = true
  const t = Date.now()
  try {
  const [ch, lg, rq, mb, us] = await Promise.all([
    api<any[]>(`/api/admin/channels?_t=${t}`).catch(() => []),
    api<any[]>(`/api/admin/crawl/logs?limit=10&_t=${t}`).catch(() => []),
    api<any[]>(`/api/admin/review-queue?status=PENDING&_t=${t}`).catch(() => []),
    api<any>(`/api/team/members?_t=${t}`).catch(() => ({ items: [] })),
    api<any>(`/api/songs?source=USER&_t=${t}`).catch(() => ({ items: [] })),
  ])
  channels.value = ch
  logs.value = lg
  reviewQueue.value = rq
  members.value = mb.items || []
  userSongs.value = us.items || []
  } catch (e: any) {
    console.error('load error:', e)
  }
  loading.value = false
}

function extractHandle(url: string): string {
  // https://youtube.com/@MarkersWorship?si=xxx → MarkersWorship
  const match = url.match(/@([a-zA-Z0-9_-]+)/)
  return match ? match[1] : ''
}

function openAddForm() {
  editingChannelId.value = null
  channelForm.value = { name: '', youtube_channel_url: '', youtube_channel_id: '', trust_level: 'HIGH' }
  showChannelForm.value = true
}

function openEditForm(ch: any) {
  editingChannelId.value = ch.id
  channelForm.value = {
    name: ch.name,
    youtube_channel_url: ch.youtube_channel_url,
    youtube_channel_id: ch.youtube_channel_id,
    trust_level: ch.trust_level,
  }
  showChannelForm.value = true
}

function closeForm() {
  showChannelForm.value = false
  editingChannelId.value = null
}

async function resolveFromUrl() {
  const url = channelForm.value.youtube_channel_url.trim()
  if (!url) { alert('URL을 입력해주세요.'); return }

  const handle = extractHandle(url)
  if (!handle) { alert('URL에서 @handle을 찾을 수 없습니다.\n예: https://youtube.com/@MarkersWorship'); return }

  resolving.value = true
  try {
    const result = await api<any>(`/api/admin/channels/resolve-id?youtube_channel_id=${encodeURIComponent(handle)}`)
    channelForm.value.youtube_channel_id = result.channel_id
    if (result.name && !channelForm.value.name) {
      channelForm.value.name = result.name
    }
  } catch (e: any) {
    alert(e.message || '채널을 찾을 수 없습니다.')
  }
  resolving.value = false
}

async function saveChannel() {
  // URL만 넣고 채널ID가 비어있으면 자동 변환 시도
  if (!channelForm.value.youtube_channel_id && channelForm.value.youtube_channel_url) {
    await resolveFromUrl()
  }

  if (!channelForm.value.youtube_channel_id) {
    alert('채널 ID를 확인할 수 없습니다.')
    return
  }

  if (!channelForm.value.name) {
    alert('사역팀 이름을 입력해주세요.')
    return
  }

  try {
    if (editingChannelId.value) {
      await api(`/api/admin/channels/${editingChannelId.value}`, {
        method: 'PUT',
        body: JSON.stringify(channelForm.value),
      })
    } else {
      await api('/api/admin/channels', {
        method: 'POST',
        body: JSON.stringify(channelForm.value),
      })
    }
    closeForm()
    await load()
  } catch (e: any) {
    alert(e.message || '저장 실패')
  }
}

async function toggleChannel(ch: any) {
  try {
    await api(`/api/admin/channels/${ch.id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: !ch.is_active }),
    })
  } catch (e: any) { alert(e.message || '수정 실패') }
  await load()
}

async function deleteChannel(ch: any) {
  if (!confirm(`"${ch.name}" 채널을 삭제하시겠습니까?`)) return
  try {
    await api(`/api/admin/channels/${ch.id}`, { method: 'DELETE' })
  } catch (e: any) { alert(e.message || '삭제 실패') }
  await load()
}

async function crawlChannel(channelId: string) {
  crawling.value = true
  try {
    const result = await api<any>(`/api/admin/crawl/${channelId}`, { method: 'POST' })
    if (result.error) {
      alert(`크롤링 실패: ${result.error}`)
    } else {
      alert(`크롤링 완료!\n영상 ${result.videos_found}개 발견\n레퍼런스 +${result.refs_added}개`)
    }
  } catch (e: any) { alert(e.message || '크롤링 실패') }
  crawling.value = false
  await load()
}

async function crawlAll() {
  crawling.value = true
  try {
    const result = await api<any>('/api/admin/crawl/all', { method: 'POST' })
    const summary = (result.results || []).map((r: any) =>
      r.error
        ? `${r.channel_name}: 실패 - ${r.error}`
        : `${r.channel_name}: 영상 ${r.videos_found}개, 레퍼런스 +${r.refs_added}개`
    ).join('\n')
    alert(`전체 크롤링 완료! (${result.channels_crawled}개 채널)\n\n${summary}`)
  } catch (e: any) { alert(e.message || '크롤링 실패') }
  crawling.value = false
  await load()
}

async function approveAsNew(rq: any) {
  try {
    await api(`/api/admin/review/${rq.id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ song_title: rq.parsed_song_title }),
    })
  } catch (e: any) { alert(e.message || '승인 실패') }
  await load()
}

async function approveWithSong(rq: any, songId: string) {
  try {
    await api(`/api/admin/review/${rq.id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ song_id: songId }),
    })
  } catch (e: any) { alert(e.message || '승인 실패') }
  await load()
}

async function approveUserSong(song: any) {
  try {
    await api(`/api/admin/songs/${song.id}/source`, {
      method: 'PUT',
      body: JSON.stringify({ source: 'MANUAL' }),
    })
    await load()
  } catch (e: any) { alert(e.message || '승인 실패') }
}

async function deleteUserSong(song: any) {
  if (!confirm(`"${song.title}" 곡을 삭제하시겠습니까?`)) return
  try {
    await api(`/api/songs/${song.id}`, { method: 'DELETE' })
    await load()
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

async function resetCrawlData() {
  if (!confirm('크롤링 데이터를 전부 삭제하시겠습니까?\n(검증 큐, 크롤링 로그, 크롤링으로 생성된 곡/레퍼런스 전부 삭제)')) return
  try {
    const result = await api<any>('/api/admin/crawl/reset', { method: 'DELETE' })
    alert(`삭제 완료!\n곡: ${result.deleted.songs}개\n레퍼런스: ${result.deleted.references}개\n검증큐: ${result.deleted.review_queue}개\n로그: ${result.deleted.crawl_logs}개`)
    await load()
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

async function rejectReview(rq: any) {
  try {
    await api(`/api/admin/review/${rq.id}/reject`, { method: 'POST' })
  } catch (e: any) { alert(e.message || '거부 실패') }
  await load()
}

async function autoApproveAll() {
  if (!confirm(`검증 큐 ${reviewQueue.value.length}개 항목을 자동 승인하시겠습니까?\n(애매한 항목은 남겨둡니다)`)) return
  try {
    const result = await api<any>(`/api/admin/review/auto-approve`, { method: 'POST' })
    alert(`자동 승인 완료!\n승인: ${result.auto_approved}개\n애매해서 남김: ${result.skipped_ambiguous}개`)
    await load()
  } catch (e: any) { alert(e.message || '자동 승인 실패') }
}

async function exportReviewQueue() {
  try {
    const data = await api<any>(`/api/admin/review-queue/export?_t=${Date.now()}`)
    if (data.count === 0) {
      alert('검증 큐가 비어있습니다.')
      return
    }
    // 클립보드 복사 (HTTPS 없으면 fallback)
    try {
      await navigator.clipboard.writeText(data.text)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = data.text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    alert(`검증 큐 ${data.count}개 항목이 클립보드에 복사되었습니다.\nClaude Code에 붙여넣으세요.`)
  } catch (e: any) {
    alert(e.message || '내보내기 실패')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>관리자</h1>

    <div v-if="loading" class="loading">불러오는 중...</div>

    <template v-else>
      <!-- 팀원 관리 -->
      <section class="section">
        <div class="section-header">
          <h2>팀원 관리 ({{ members.length }}명)</h2>
          <button class="btn" @click="openMemberAdd">팀원 추가</button>
        </div>

        <div v-if="showMemberForm" class="add-form">
          <h3>{{ editingMemberId ? '팀원 수정' : '팀원 추가' }}</h3>
          <label>이름</label>
          <input v-model="memberForm.name" class="input" placeholder="이름" />
          <label>포지션</label>
          <select v-model="memberForm.position" class="input">
            <option v-for="p in POSITIONS" :key="p" :value="p">{{ p }}</option>
          </select>
          <div class="form-actions">
            <button class="btn-accent" @click="saveMember">{{ editingMemberId ? '수정' : '추가' }}</button>
            <button class="btn" @click="showMemberForm = false">취소</button>
          </div>
        </div>

        <div v-if="members.length === 0" class="empty">등록된 팀원이 없습니다</div>
        <div class="member-list">
          <div v-for="m in members" :key="m.id" :class="['member-card', { inactive: !m.is_active }]">
            <div class="member-info">
              <span class="member-name">{{ m.name }}</span>
              <span class="position-badge">{{ m.position }}</span>
              <span v-if="!m.is_active" class="inactive-label">비활성</span>
            </div>
            <div class="member-actions">
              <button class="btn-sm" @click="openMemberEdit(m)">수정</button>
              <button class="btn-sm" @click="toggleMember(m)">{{ m.is_active ? '비활성화' : '활성화' }}</button>
              <button class="btn-sm danger" @click="deleteMember(m)">삭제</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 유저 등록 곡 정제 -->
      <section v-if="userSongs.length > 0" class="section">
        <h2>유저 등록 곡 ({{ userSongs.length }})</h2>
        <div class="user-song-list">
          <div v-for="song in userSongs" :key="song.id" class="user-song-card">
            <div class="us-info">
              <span class="us-title">{{ song.title }}</span>
              <span v-if="song.artist" class="us-artist">{{ song.artist }}</span>
              <span v-if="song.default_key" class="key-badge">{{ song.default_key }}</span>
            </div>
            <div class="us-actions">
              <NuxtLink :to="`/songs/${song.id}`" class="btn-sm">상세</NuxtLink>
              <button class="btn-sm approve" @click="approveUserSong(song)">승인</button>
              <button class="btn-sm danger" @click="deleteUserSong(song)">삭제</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 채널 관리 -->
      <section class="section">
        <div class="section-header">
          <h2>크롤링 채널 ({{ channels.length }})</h2>
          <div class="section-actions">
            <button class="btn" @click="openAddForm">채널 추가</button>
            <button class="btn-accent" :disabled="crawling" @click="crawlAll">
              {{ crawling ? '크롤링 중...' : '전체 크롤링' }}
            </button>
            <button class="btn-sm danger" @click="resetCrawlData">초기화</button>
          </div>
        </div>

        <!-- 채널 추가/편집 폼 -->
        <div v-if="showChannelForm" class="add-form">
          <h3>{{ editingChannelId ? '채널 수정' : '채널 추가' }}</h3>

          <label>유튜브 채널 URL</label>
          <div class="url-row">
            <input v-model="channelForm.youtube_channel_url" class="input" placeholder="https://youtube.com/@MarkersWorship" />
            <div class="url-actions">
              <button class="btn" :disabled="resolving" @click="resolveFromUrl">
                {{ resolving ? '확인 중...' : '자동입력' }}
              </button>
            </div>
          </div>

          <label>사역팀 이름</label>
          <input v-model="channelForm.name" class="input" placeholder="자동입력됩니다" />

          <label>채널 ID</label>
          <input v-model="channelForm.youtube_channel_id" class="input" placeholder="자동입력됩니다 (UC...)" readonly />

          <label>신뢰도</label>
          <select v-model="channelForm.trust_level" class="input">
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>

          <div class="form-actions">
            <button class="btn-accent" @click="saveChannel">{{ editingChannelId ? '수정' : '등록' }}</button>
            <button class="btn" @click="closeForm">취소</button>
          </div>
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
              <span>{{ ch.youtube_channel_id }}</span>
              <span v-if="ch.last_crawled_at"> · 마지막: {{ ch.last_crawled_at }}</span>
            </div>
            <div class="ch-actions">
              <button class="btn-sm" @click="crawlChannel(ch.id)" :disabled="crawling">크롤링</button>
              <button class="btn-sm" @click="openEditForm(ch)">수정</button>
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
        <div class="section-header">
          <h2>검증 큐 ({{ reviewQueue.length }})</h2>
          <div v-if="reviewQueue.length > 0" class="section-actions">
            <button class="btn-accent" @click="autoApproveAll">자동 승인</button>
            <button class="btn" @click="exportReviewQueue">내보내기</button>
          </div>
        </div>
        <div v-if="reviewQueue.length === 0" class="empty">대기 중인 항목 없음</div>
        <div v-for="rq in reviewQueue" :key="rq.id" class="review-card">
          <div class="rv-info">
            <div class="rv-title">{{ rq.video_title }}</div>
            <div class="rv-parsed">파싱된 곡명: <strong>{{ rq.parsed_song_title || '(없음)' }}</strong></div>
            <a :href="rq.youtube_url" target="_blank" class="rv-link">유튜브에서 보기</a>

            <!-- 유사곡 후보 -->
            <div v-if="(rq.candidates || []).length > 0" class="rv-candidates">
              <div class="rv-candidates-label">비슷한 곡이 DB에 있어요:</div>
              <div v-for="c in rq.candidates" :key="c.id" class="candidate-item">
                <span>{{ c.title }}</span>
                <button class="btn-xs approve" @click="approveWithSong(rq, c.id)">이 곡에 추가</button>
              </div>
            </div>
          </div>
          <div class="rv-actions">
            <button class="btn-sm approve" @click="approveAsNew(rq)">새 곡으로 등록</button>
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
        </div>
        <div v-for="log in logs.filter(l => l.error_message)" :key="'err-'+log.id" class="log-error-detail">
          {{ log.error_message }}
        </div>
      </section>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

h1 { font-size: 24px; font-weight: 800; margin-bottom: 24px; }
h2 { font-size: 18px; font-weight: 700; margin-bottom: 12px; }
h3 { font-size: 15px; font-weight: 700; margin: 0 0 8px; }

label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-dim);
  margin-top: 4px;
}

.btn { @include btn; }
.btn-accent { @include btn-accent; }
.input { @include input; }

.section { margin-bottom: 32px; }

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
  h2 { margin: 0; }
}

.section-actions { display: flex; gap: 8px; }

.add-form {
  @include card;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.url-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  .url-actions { display: flex; justify-content: flex-end; }
}

.form-actions { display: flex; gap: 8px; margin-top: 8px; }

.channel-list { display: flex; flex-direction: column; gap: 8px; }

.channel-card { @include card; padding: 14px 16px; }

.ch-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.ch-name { font-weight: 600; }

.trust {
  padding: 1px 8px; border-radius: 6px; font-size: 12px; font-weight: 700;
  &.high { background: var(--green-soft); color: var(--green); }
  &.medium { background: var(--accent-soft); color: var(--accent); }
  &.low { background: var(--red-soft); color: var(--red); }
}

.active { color: var(--green); font-size: 12px; }
.inactive { color: var(--red); font-size: 12px; }

.ch-meta { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; word-break: break-all; }
.ch-actions { display: flex; gap: 6px; flex-wrap: wrap; }

.btn-sm {
  padding: 4px 12px; border-radius: 8px; border: 1px solid var(--line);
  background: rgba(255,255,255,0.02); color: var(--text); font-size: 12px; cursor: pointer;
  &:hover { background: rgba(255,255,255,0.05); }
  &.danger { color: var(--red); &:hover { background: var(--red-soft); } }
  &.approve { color: var(--green); &:hover { background: var(--green-soft); } }
  &:disabled { opacity: .5; cursor: not-allowed; }
}

.review-card {
  @include card; padding: 14px 16px;
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 8px; gap: 12px;
}

.rv-info { flex: 1; min-width: 0; }
.rv-title { font-weight: 600; margin-bottom: 4px; word-break: break-word; }
.rv-parsed { font-size: 13px; color: var(--text-dim); margin-bottom: 4px; }
.rv-link { font-size: 12px; color: var(--accent); &:hover { text-decoration: underline; } }
.rv-actions { display: flex; gap: 6px; flex-shrink: 0; flex-direction: column; }

.rv-candidates {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
  border: 1px solid var(--line);
}

.rv-candidates-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--green);
  margin-bottom: 6px;
}

.candidate-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
  gap: 8px;
}

.btn-xs {
  padding: 2px 10px; border-radius: 6px; border: 1px solid var(--line);
  background: transparent; font-size: 11px; cursor: pointer;
  &.approve { color: var(--green); &:hover { background: var(--green-soft); } }
}

.log-card {
  @include card; padding: 10px 14px;
  display: flex; gap: 14px; align-items: center;
  margin-bottom: 6px; font-size: 13px; flex-wrap: wrap;
}

.log-status {
  padding: 1px 8px; border-radius: 6px; font-size: 12px; font-weight: 700;
  &.success { background: var(--green-soft); color: var(--green); }
  &.failed { background: var(--red-soft); color: var(--red); }
  &.running { background: var(--accent-soft); color: var(--accent); }
}

.log-time { color: var(--text-dim); }

.log-error-detail {
  padding: 8px 14px; font-size: 12px; color: var(--red);
  background: var(--red-soft); border-radius: var(--radius);
  margin-bottom: 6px; word-break: break-all;
}

.user-song-list { display: flex; flex-direction: column; gap: 6px; }

.user-song-card {
  @include card;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.us-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.us-title { font-weight: 600; }
.us-artist { font-size: 13px; color: var(--text-dim); }

.key-badge {
  background: var(--accent-soft);
  color: var(--accent);
  padding: 1px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}

.us-actions { display: flex; gap: 6px; flex-shrink: 0; }

.member-list { display: flex; flex-direction: column; gap: 6px; }

.member-card {
  @include card;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;

  &.inactive { opacity: 0.5; }
}

.member-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.member-name { font-weight: 600; }

.position-badge {
  background: var(--accent-soft);
  color: var(--accent);
  padding: 1px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}

.inactive-label { font-size: 12px; color: var(--red); }

.member-actions { display: flex; gap: 6px; flex-shrink: 0; }

.loading, .empty { text-align: center; padding: 20px; color: var(--text-dim); }

@media (max-width: 640px) {
  .section-header { flex-direction: column; align-items: flex-start; }
  .review-card { flex-direction: column; align-items: flex-start; }
  .url-row { flex-direction: column; }
}
</style>
