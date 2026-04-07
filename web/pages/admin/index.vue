<script setup lang="ts">
definePageMeta({ middleware: 'admin' })
const { api } = useApi()

const channels = ref<any[]>([])
const logs = ref<any[]>([])
const reviewQueue = ref<any[]>([])
const rqTotal = ref(0)
const rqFetching = ref(false)
const members = ref<any[]>([])
const userSongs = ref<any[]>([])
const filterKeywords = ref<any[]>([])
const newKeyword = ref('')
const loading = ref(true)
const crawling = ref(false)

const COMMON_KEYS = ['C', 'D', 'E', 'F', 'G', 'A', 'Bb', 'B']
// 검증 큐 row별 로컬 상태 (키/빠르기)
const rqKeys = ref<Record<string, string[]>>({})
const rqTempo = ref<Record<string, string>>({})

function toggleRqKey(rqId: string, key: string) {
  if (!rqKeys.value[rqId]) rqKeys.value[rqId] = []
  const arr = rqKeys.value[rqId]
  const idx = arr.indexOf(key)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(key)
}
function setRqTempo(rqId: string, tempo: string) {
  rqTempo.value[rqId] = rqTempo.value[rqId] === tempo ? '' : tempo
}

// 제목 입력 자동 검색 (검증 큐)
const titleSearchCache = ref<Record<string, any[]>>({})
const titleSearchTimers = {} as Record<string, ReturnType<typeof setTimeout>>

async function titleSearch(rq: any) {
  const q = (rq.parsed_song_title || '').trim()
  if (!q) { titleSearchCache.value[rq.id] = []; return }
  const res = await api<any>(`/api/songs?q=${encodeURIComponent(q)}&limit=5&_t=${Date.now()}`).catch(() => ({ items: [] }))
  titleSearchCache.value[rq.id] = res.items || []
}

function onTitleInput(rq: any) {
  clearTimeout(titleSearchTimers[rq.id])
  titleSearchTimers[rq.id] = setTimeout(() => titleSearch(rq), 400)
}

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

// 중복 곡 정리
const dupGroups = ref<any[]>([])
const dupLoading = ref(false)
const dupMerging = ref<string | null>(null)  // merging group normalized key
const dupKeepChoice = ref<Record<string, string>>({})  // normalized → keep song id
const dupTitleEdit = ref<Record<string, string>>({})  // normalized → 편집된 target 제목
const dupMergeSelection = ref<Record<string, Set<string>>>({})  // normalized → 병합할 song id 집합
const dupHideSelection = ref<Set<string>>(new Set())  // 숨길 그룹의 group_key 집합
const dupHiding = ref(false)
const showDupModal = ref(false)

async function openDupModal() {
  showDupModal.value = true
  dupLoading.value = true
  try {
    const res = await api<any>(`/api/admin/songs/duplicate-candidates?_t=${Date.now()}`)
    dupGroups.value = res.groups || []
    // 초기 keep 선택: 서버가 추천한 suggested_keep_id
    const init: Record<string, string> = {}
    const initTitle: Record<string, string> = {}
    const initSel: Record<string, Set<string>> = {}
    for (const g of dupGroups.value) {
      init[g.normalized] = g.suggested_keep_id
      const keep = g.songs.find((s: any) => s.id === g.suggested_keep_id)
      initTitle[g.normalized] = keep?.title || ''
      // 기본: keep 외 전부 선택 (기존 동작 유지)
      initSel[g.normalized] = new Set(
        g.songs.filter((s: any) => s.id !== g.suggested_keep_id).map((s: any) => s.id)
      )
    }
    dupKeepChoice.value = init
    dupTitleEdit.value = initTitle
    dupMergeSelection.value = initSel
    dupHideSelection.value = new Set()
  } catch (e: any) {
    alert(e.message || '중복 곡 조회 실패')
    showDupModal.value = false
  }
  dupLoading.value = false
}

function closeDupModal() {
  showDupModal.value = false
  dupGroups.value = []
  dupKeepChoice.value = {}
  dupTitleEdit.value = {}
  dupMergeSelection.value = {}
  dupHideSelection.value = new Set()
}

function toggleDupHide(groupKey: string) {
  if (!groupKey) return
  const sel = dupHideSelection.value
  if (sel.has(groupKey)) sel.delete(groupKey)
  else sel.add(groupKey)
  dupHideSelection.value = new Set(sel)
}

async function applyDupHide() {
  const keys = Array.from(dupHideSelection.value)
  if (!keys.length) { alert('숨길 그룹을 선택해주세요.'); return }
  if (!confirm(`${keys.length}개 그룹을 숨김 처리합니다.\n계속하시겠습니까?`)) return
  dupHiding.value = true
  try {
    await api('/api/admin/songs/dedup-ignore', {
      method: 'POST',
      body: JSON.stringify({ group_keys: keys }),
    })
    dupGroups.value = dupGroups.value.filter((g: any) => !dupHideSelection.value.has(g.group_key))
    dupHideSelection.value = new Set()
  } catch (e: any) {
    alert(e.message || '숨김 처리 실패')
  }
  dupHiding.value = false
}

function onDupKeepChange(group: any) {
  // 라디오 변경 시: 제목 리셋 + 병합 선택에서 새 keep 제외
  const keepId = dupKeepChoice.value[group.normalized]
  const keep = group.songs.find((s: any) => s.id === keepId)
  if (keep) dupTitleEdit.value[group.normalized] = keep.title || ''
  const sel = dupMergeSelection.value[group.normalized]
  if (sel) sel.delete(keepId)
}

function toggleDupMerge(group: any, songId: string) {
  const sel = dupMergeSelection.value[group.normalized]
  if (!sel) return
  if (sel.has(songId)) sel.delete(songId)
  else sel.add(songId)
  // Set 변이를 reactivity에 알리기 위해 새 Set으로 교체
  dupMergeSelection.value[group.normalized] = new Set(sel)
}

async function mergeDupGroup(group: any) {
  const keepId = dupKeepChoice.value[group.normalized]
  if (!keepId) { alert('남길 곡을 선택해주세요.'); return }
  const sel = dupMergeSelection.value[group.normalized] || new Set<string>()
  const sourceIds = group.songs
    .map((s: any) => s.id)
    .filter((id: string) => id !== keepId && sel.has(id))
  if (!sourceIds.length) { alert('병합할 곡을 선택해주세요.'); return }
  const kept = group.songs.find((s: any) => s.id === keepId)
  const newTitle = (dupTitleEdit.value[group.normalized] || '').trim()
  const finalTitle = newTitle || kept.title
  if (!confirm(`"${finalTitle}"로 ${sourceIds.length}곡을 병합합니다.\n계속하시겠습니까?`)) return
  dupMerging.value = group.normalized
  try {
    await api('/api/admin/songs/merge', {
      method: 'POST',
      body: JSON.stringify({
        source_ids: sourceIds,
        target_id: keepId,
        target_title: newTitle && newTitle !== kept.title ? newTitle : undefined,
      }),
    })
    // 병합된 그룹을 목록에서 제거
    dupGroups.value = dupGroups.value.filter((g: any) => g.normalized !== group.normalized)
  } catch (e: any) {
    alert(e.message || '병합 실패')
  }
  dupMerging.value = null
}

// 곡 DB 재정리 (parser/filter 일괄 적용)
const showRecleanModal = ref(false)
const recleanLoading = ref(false)
const recleanApplying = ref(false)
const recleanPreview = ref<any>(null)

async function openRecleanModal() {
  showRecleanModal.value = true
  recleanLoading.value = true
  recleanPreview.value = null
  try {
    recleanPreview.value = await api<any>(`/api/admin/songs/reclean?dry_run=true&_t=${Date.now()}`, { method: 'POST' })
  } catch (e: any) {
    alert(e.message || '재정리 미리보기 실패')
    showRecleanModal.value = false
  }
  recleanLoading.value = false
}

function closeRecleanModal() {
  showRecleanModal.value = false
  recleanPreview.value = null
}

async function applyReclean() {
  if (!recleanPreview.value) return
  const t = recleanPreview.value.title_changes_total
  if (!confirm(`제목 변경 ${t}건을 실제 적용합니다.\n계속하시겠습니까?`)) return
  recleanApplying.value = true
  try {
    const res = await api<any>(`/api/admin/songs/reclean?dry_run=false`, { method: 'POST' })
    alert(`적용 완료!\n제목 변경: ${res.title_changes}건`)
    closeRecleanModal()
    await load()
  } catch (e: any) {
    alert(e.message || '재정리 실패')
  }
  recleanApplying.value = false
}

// 채널 등록/편집
const showChannelForm = ref(false)
const editingChannelId = ref<string | null>(null)
const channelForm = ref({ name: '', youtube_channel_url: '', youtube_channel_id: '', trust_level: 'HIGH' })
const resolving = ref(false)

async function loadReviewQueue() {
  const res = await api<any>(`/api/admin/review-queue?status=PENDING&limit=10&offset=0&_t=${Date.now()}`).catch(() => ({ total: 0, items: [] }))
  rqTotal.value = res.total ?? 0
  reviewQueue.value = res.items ?? []
}

async function refillQueue() {
  if (rqFetching.value) return
  if (reviewQueue.value.length >= 10) return
  if (reviewQueue.value.length >= rqTotal.value) return
  rqFetching.value = true
  try {
    const existing = new Set(reviewQueue.value.map((r: any) => r.id))
    const res = await api<any>(`/api/admin/review-queue?status=PENDING&limit=10&offset=0&_t=${Date.now()}`)
    rqTotal.value = res.total ?? 0
    const newItems = (res.items ?? []).filter((r: any) => !existing.has(r.id))
    const needed = 10 - reviewQueue.value.length
    reviewQueue.value.push(...newItems.slice(0, needed))
  } catch {}
  rqFetching.value = false
}

async function load() {
  loading.value = true
  const t = Date.now()
  try {
  const [ch, lg, mb, us, fk] = await Promise.all([
    api<any[]>(`/api/admin/channels?_t=${t}`).catch(() => []),
    api<any[]>(`/api/admin/crawl/logs?limit=10&_t=${t}`).catch(() => []),
    api<any>(`/api/team/members?_t=${t}`).catch(() => ({ items: [] })),
    api<any>(`/api/songs?source=USER&_t=${t}`).catch(() => ({ items: [] })),
    api<any[]>(`/api/admin/filter-keywords?_t=${t}`).catch(() => []),
  ])
  channels.value = ch
  logs.value = lg
  members.value = mb.items || []
  userSongs.value = us.items || []
  filterKeywords.value = fk
  await loadReviewQueue()
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

async function crawlSetlistsChannel(channelId: string) {
  crawling.value = true
  try {
    const result = await api<any>(`/api/admin/crawl-setlists/${channelId}?max_videos=10`, { method: 'POST' })
    if (result.error) {
      alert(`세트리스트 크롤 실패: ${result.error}`)
    } else {
      alert(`세트리스트 크롤 완료!\n영상 ${result.videos_scanned}개 스캔\n신규 곡 +${result.songs_created}개\n키 보강 +${result.keys_added}개\n레퍼런스 +${result.refs_added}개`)
    }
  } catch (e: any) { alert(e.message || '세트리스트 크롤 실패') }
  crawling.value = false
  await load()
}

async function crawlSetlistsAll() {
  if (!confirm('전체 활성 채널에서 예배 실황 영상의 세트리스트를 추출합니다.\n(YouTube API quota를 꽤 사용합니다)')) return
  crawling.value = true
  try {
    const result = await api<any>('/api/admin/crawl-setlists/all?max_videos=10', { method: 'POST' })
    const summary = (result.results || []).map((r: any) =>
      r.error
        ? `${r.channel_name}: 실패 - ${r.error}`
        : `${r.channel_name}: 영상 ${r.videos_scanned ?? 0}개, 신규 곡 +${r.songs_created ?? 0}, 키 +${r.keys_added ?? 0}, ref +${r.refs_added ?? 0}`
    ).join('\n')
    alert(`전체 세트리스트 크롤 완료! (${result.channels_crawled}개 채널)\n\n${summary}`)
  } catch (e: any) { alert(e.message || '세트리스트 크롤 실패') }
  crawling.value = false
  await load()
}

function removeRq(id: string) {
  const idx = reviewQueue.value.findIndex(r => r.id === id)
  if (idx >= 0) {
    reviewQueue.value.splice(idx, 1)
    rqTotal.value = Math.max(0, rqTotal.value - 1)
  }
  refillQueue()
}

async function approveAsNew(rq: any) {
  const title = (rq.parsed_song_title || '').trim()
  if (!title) { alert('곡 제목을 입력해주세요.'); return }
  try {
    const keys = rqKeys.value[rq.id]?.length ? rqKeys.value[rq.id] : undefined
    const tempo = rqTempo.value[rq.id] || undefined
    await api(`/api/admin/review/${rq.id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ song_title: title, keys, tempo }),
    })
    removeRq(rq.id)
  } catch (e: any) { alert(e.message || '승인 실패') }
}

async function approveWithSong(rq: any, songId: string) {
  try {
    await api(`/api/admin/review/${rq.id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ song_id: songId }),
    })
    removeRq(rq.id)
  } catch (e: any) { alert(e.message || '승인 실패') }
}

// 기존곡 검색 (row별)
const searchCache = ref<Record<string, any[]>>({})
const searchBusy = ref<Record<string, boolean>>({})

async function searchSongs(rq: any) {
  const q = (rq.search_query || '').trim()
  if (!q) { searchCache.value[rq.id] = []; return }
  searchBusy.value[rq.id] = true
  try {
    const res = await api<any>(`/api/songs?q=${encodeURIComponent(q)}&limit=10&_t=${Date.now()}`)
    searchCache.value[rq.id] = res.items || []
  } catch (e: any) {
    searchCache.value[rq.id] = []
  }
  searchBusy.value[rq.id] = false
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

async function addFilterKeyword() {
  const kw = newKeyword.value.trim()
  if (!kw) return
  try {
    const item = await api<any>('/api/admin/filter-keywords', { method: 'POST', body: JSON.stringify({ keyword: kw }) })
    filterKeywords.value.push(item)
    newKeyword.value = ''
  } catch (e: any) { alert(e.message || '추가 실패') }
}

async function deleteFilterKeyword(kw: any) {
  try {
    await api(`/api/admin/filter-keywords/${kw.id}`, { method: 'DELETE' })
    filterKeywords.value = filterKeywords.value.filter(k => k.id !== kw.id)
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
    removeRq(rq.id)
  } catch (e: any) { alert(e.message || '거부 실패') }
}

async function deleteSetlistRefs() {
  if (!confirm('예배 실황 세트리스트로 생성된 타임스탬프 레퍼런스를 모두 삭제할까요?\n(이후 세트리스트 크롤은 곡/키만 추가하고 ref는 만들지 않습니다)')) return
  try {
    const res = await api<any>(`/api/admin/songs/delete-setlist-refs`, { method: 'POST' })
    alert(`삭제 완료: ${res.deleted}건`)
    await load()
  } catch (e: any) { alert(e.message || '삭제 실패') }
}

async function reparseTitles() {
  if (!confirm('PENDING 큐 항목의 제목을 현재 파서로 재계산하시겠습니까?')) return
  try {
    const result = await api<any>(`/api/admin/review/reparse-titles`, { method: 'POST' })
    alert(`재파싱 완료!\n총 ${result.total}개 중 ${result.updated}개 업데이트됨`)
    await load()
  } catch (e: any) { alert(e.message || '재파싱 실패') }
}

async function autoApproveAll() {
  if (!confirm(`검증 큐 ${rqTotal.value}개 항목을 자동 승인하시겠습니까?\n(애매한 항목은 남겨둡니다)`)) return
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
            <button class="btn" :disabled="crawling" @click="crawlSetlistsAll">
              {{ crawling ? '...' : '전체 세트리스트' }}
            </button>
            <button class="btn" @click="openRecleanModal">곡 DB 재정리</button>
            <button class="btn" @click="deleteSetlistRefs">세트리스트 ref 삭제</button>
            <button class="btn" @click="openDupModal">중복 곡 정리</button>
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
              <button class="btn-sm" @click="crawlSetlistsChannel(ch.id)" :disabled="crawling">세트리스트</button>
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
          <h2>검증 큐 ({{ reviewQueue.length }} / {{ rqTotal }})</h2>
          <div v-if="rqTotal > 0" class="section-actions">
            <button class="btn" @click="reparseTitles">제목 재파싱</button>
            <button class="btn-accent" @click="autoApproveAll">자동 승인</button>
            <button class="btn" @click="exportReviewQueue">내보내기</button>
          </div>
        </div>
        <div v-if="rqTotal === 0" class="empty">대기 중인 항목 없음</div>
        <div v-if="rqFetching" class="rq-loading">불러오는 중...</div>
        <div v-for="rq in reviewQueue" :key="rq.id" class="review-card">
          <div class="rv-video" v-if="rq.youtube_video_id">
            <iframe
              :src="`https://www.youtube.com/embed/${rq.youtube_video_id}`"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
            />
          </div>
          <div class="rv-info">
            <div class="rv-title">{{ rq.video_title }}</div>
            <div class="rv-parsed-row">
              <label>파싱된 곡명</label>
              <input
                v-model="rq.parsed_song_title"
                type="text"
                class="rv-title-input"
                placeholder="곡 제목을 입력하세요"
                @input="onTitleInput(rq)"
              />
            </div>

            <!-- 제목 자동 검색 결과 -->
            <div v-if="titleSearchCache[rq.id] && titleSearchCache[rq.id].length > 0" class="rv-candidates rv-title-matches">
              <div class="rv-candidates-label">곡명이 같은 곡이 이미 있어요:</div>
              <div v-for="s in titleSearchCache[rq.id]" :key="s.id" class="candidate-item">
                <span>{{ s.title }}<span v-if="s.artist" class="rv-artist"> · {{ s.artist }}</span></span>
                <button class="btn-xs approve" @click="approveWithSong(rq, s.id)">이 곡에 추가</button>
              </div>
            </div>

            <!-- 키 선택 (새 곡 등록 시 적용) -->
            <div class="rv-field-row">
              <label>키</label>
              <div class="rv-key-chips">
                <button
                  v-for="k in COMMON_KEYS" :key="k" type="button"
                  :class="['key-chip-sm', { selected: (rqKeys[rq.id] || []).includes(k) }]"
                  @click="toggleRqKey(rq.id, k)"
                >{{ k }}</button>
              </div>
            </div>

            <!-- 빠르기 선택 (새 곡 등록 시 적용) -->
            <div class="rv-field-row">
              <label>빠르기</label>
              <div class="rv-tempo-chips">
                <button
                  type="button"
                  :class="['tempo-chip', { selected: rqTempo[rq.id] === 'FAST' }]"
                  @click="setRqTempo(rq.id, 'FAST')"
                >빠른곡</button>
                <button
                  type="button"
                  :class="['tempo-chip', { selected: rqTempo[rq.id] === 'SLOW' }]"
                  @click="setRqTempo(rq.id, 'SLOW')"
                >느린곡</button>
              </div>
            </div>

            <a :href="rq.youtube_url" target="_blank" class="rv-link">유튜브에서 보기 ↗</a>

            <!-- 유사곡 후보 (서버 제공) -->
            <div v-if="(rq.candidates || []).length > 0" class="rv-candidates">
              <div class="rv-candidates-label">비슷한 곡이 DB에 있어요:</div>
              <div v-for="c in rq.candidates" :key="c.id" class="candidate-item">
                <span>{{ c.title }}</span>
                <button class="btn-xs approve" @click="approveWithSong(rq, c.id)">이 곡에 추가</button>
              </div>
            </div>

            <!-- 기존곡 검색 -->
            <div class="rv-search">
              <div class="rv-search-row">
                <input
                  v-model="rq.search_query"
                  type="text"
                  class="rv-search-input"
                  placeholder="기존 곡 검색..."
                  @keyup.enter="searchSongs(rq)"
                />
                <button class="btn-xs" @click="searchSongs(rq)" :disabled="searchBusy[rq.id]">
                  {{ searchBusy[rq.id] ? '...' : '검색' }}
                </button>
              </div>
              <div v-if="searchCache[rq.id] && searchCache[rq.id].length > 0" class="rv-search-results">
                <div v-for="s in searchCache[rq.id]" :key="s.id" class="candidate-item">
                  <span>{{ s.title }}<span v-if="s.artist" class="rv-artist"> · {{ s.artist }}</span></span>
                  <button class="btn-xs approve" @click="approveWithSong(rq, s.id)">이 곡에 추가</button>
                </div>
              </div>
              <div v-else-if="searchCache[rq.id] && searchCache[rq.id].length === 0" class="rv-search-empty">
                검색 결과 없음
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

      <!-- 필터 키워드 관리 -->
      <section class="section">
        <h2>크롤링 필터 키워드</h2>
        <p class="section-desc">영상 제목에 이 단어가 포함되면 크롤링에서 제외됩니다.</p>
        <div class="keyword-input-row">
          <input v-model="newKeyword" type="text" class="input-field" placeholder="키워드 추가..." @keyup.enter="addFilterKeyword" />
          <button class="btn-accent" @click="addFilterKeyword">추가</button>
        </div>
        <div v-if="filterKeywords.length === 0" class="empty">등록된 키워드 없음</div>
        <div class="keyword-list">
          <div v-for="kw in filterKeywords" :key="kw.id" class="keyword-chip">
            <span>{{ kw.keyword }}</span>
            <button @click="deleteFilterKeyword(kw)" class="keyword-delete">✕</button>
          </div>
        </div>
      </section>

    </template>

    <!-- 곡 DB 재정리 모달 -->
    <Teleport to="body">
      <div v-if="showRecleanModal" class="modal-overlay" @click.self="closeRecleanModal">
        <div class="modal-panel">
          <div class="modal-header">
            <h3>곡 DB 재정리 (미리보기)</h3>
            <button class="btn-sm" @click="closeRecleanModal">닫기</button>
          </div>
          <div v-if="recleanLoading" class="dup-empty">스캔 중...</div>
          <div v-else-if="recleanPreview" class="dup-group-list">
            <div class="reclean-summary">
              <div>제목 변경 후보: <strong>{{ recleanPreview.title_changes_total }}</strong>건</div>
              <div class="dup-empty" style="padding: 8px 0; font-size: 12px;">
                * source=CRAWLED 곡만 대상. 수동 곡과 레퍼런스는 건드리지 않음.
              </div>
            </div>

            <div v-if="recleanPreview.title_changes?.length" class="dup-group">
              <div class="dup-group-title">제목 변경 (앞 100건)</div>
              <div class="reclean-list">
                <div v-for="c in recleanPreview.title_changes" :key="c.id" class="reclean-row">
                  <span class="reclean-old">{{ c.old }}</span>
                  <span class="reclean-arrow">→</span>
                  <span class="reclean-new">{{ c.new }}</span>
                </div>
              </div>
            </div>

            <div class="dup-group-actions" style="margin-top: 12px;">
              <button
                class="btn-accent"
                :disabled="recleanApplying || recleanPreview.title_changes_total === 0"
                @click="applyReclean"
              >
                {{ recleanApplying ? '적용 중...' : '실제 적용' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 중복 곡 정리 모달 -->
    <Teleport to="body">
      <div v-if="showDupModal" class="modal-overlay" @click.self="closeDupModal">
        <div class="modal-panel">
          <div class="modal-header">
            <h3>중복 곡 정리 ({{ dupGroups.length }} 그룹)</h3>
            <div class="dup-header-actions">
              <button
                class="btn-sm"
                :disabled="dupHiding || !dupHideSelection.size"
                @click="applyDupHide"
              >
                {{ dupHiding ? '숨기는 중...' : `선택한 그룹 숨기기 (${dupHideSelection.size})` }}
              </button>
              <button class="btn-sm" @click="closeDupModal">닫기</button>
            </div>
          </div>
          <div v-if="dupLoading" class="dup-empty">불러오는 중...</div>
          <div v-else-if="!dupGroups.length" class="dup-empty">중복 후보가 없습니다.</div>
          <div v-else class="dup-group-list">
            <div v-for="g in dupGroups" :key="g.normalized" class="dup-group">
              <div class="dup-group-header">
                <div class="dup-group-title">{{ g.normalized }}</div>
                <label class="dup-hide-toggle">
                  <input
                    type="checkbox"
                    :checked="dupHideSelection.has(g.group_key)"
                    @change="toggleDupHide(g.group_key)"
                  />
                  이 조합 숨기기
                </label>
              </div>
              <div class="dup-song-rows">
                <div v-for="s in g.songs" :key="s.id" class="dup-song-row">
                  <input
                    type="radio"
                    :name="`dup-keep-${g.normalized}`"
                    :value="s.id"
                    v-model="dupKeepChoice[g.normalized]"
                    @change="onDupKeepChange(g)"
                    title="남길 곡"
                  />
                  <input
                    type="checkbox"
                    :checked="dupMergeSelection[g.normalized]?.has(s.id)"
                    :disabled="dupKeepChoice[g.normalized] === s.id"
                    @change="toggleDupMerge(g, s.id)"
                    title="병합할 곡"
                  />
                  <span class="dup-song-title">{{ s.title }}</span>
                  <span class="dup-song-meta">
                    {{ s.default_key || '키없음' }} · 레퍼런스 {{ s.ref_count }}
                  </span>
                </div>
              </div>
              <div class="dup-legend">○ 남길 곡 / ☑ 병합할 곡 (체크 해제하면 그대로 둠)</div>
              <div class="dup-title-edit">
                <label>병합 후 제목</label>
                <input
                  class="input"
                  v-model="dupTitleEdit[g.normalized]"
                  placeholder="제목 수정"
                />
              </div>
              <div class="dup-group-actions">
                <button
                  class="btn-accent btn-sm"
                  :disabled="dupMerging === g.normalized"
                  @click="mergeDupGroup(g)"
                >
                  {{ dupMerging === g.normalized ? '병합 중...' : '이 그룹 병합' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
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
  margin-bottom: 8px; gap: 14px;
}

.rv-video {
  flex-shrink: 0;
  width: 320px;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  overflow: hidden;
  background: #000;

  iframe { width: 100%; height: 100%; border: 0; }
}

.rv-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.rv-title { font-weight: 600; word-break: break-word; font-size: 14px; }

.rv-parsed-row {
  display: flex; flex-direction: column; gap: 4px;
  label { font-size: 11px; font-weight: 600; color: var(--text-dim); }
}
.rv-title-input {
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
  &:focus { outline: none; border-color: var(--accent); }
}

.rv-link { font-size: 12px; color: var(--accent); align-self: flex-start; &:hover { text-decoration: underline; } }

.rv-field-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  label { font-size: 11px; color: var(--text-dim); width: 36px; flex-shrink: 0; }
}
.rv-key-chips, .rv-tempo-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.key-chip-sm {
  padding: 2px 7px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  &:hover { border-color: var(--accent); color: var(--accent); }
  &.selected { background: var(--accent); border-color: var(--accent); color: #fff; }
}
.tempo-chip {
  padding: 2px 10px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  &:hover { border-color: var(--accent); color: var(--accent); }
  &.selected { background: var(--accent); border-color: var(--accent); color: #fff; }
}

.rv-actions { display: flex; gap: 6px; flex-shrink: 0; flex-direction: column; }

.rv-search {
  margin-top: 4px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.02);
  border-radius: 8px;
  border: 1px solid var(--line);
}
.rv-search-row { display: flex; gap: 6px; }
.rv-search-input {
  flex: 1; min-width: 0;
  padding: 5px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font-size: 12px;
  &:focus { outline: none; border-color: var(--accent); }
}
.rv-search-results { margin-top: 6px; display: flex; flex-direction: column; }
.rv-search-empty { margin-top: 6px; font-size: 12px; color: var(--text-dim); }
.rv-artist { color: var(--text-dim); font-size: 12px; }

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

.loading, .empty, .rq-loading { text-align: center; padding: 20px; color: var(--text-dim); }

.section-desc { font-size: 13px; color: var(--text-dim); margin-bottom: 12px; }

.rv-title-matches { border-color: var(--accent); }

.keyword-input-row { display: flex; gap: 8px; margin-bottom: 12px; }
.keyword-list { display: flex; flex-wrap: wrap; gap: 6px; }
.keyword-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: 20px;
  background: var(--accent-soft); color: var(--accent);
  font-size: 13px;
}
.keyword-delete {
  background: none; border: none; cursor: pointer;
  color: var(--accent); font-size: 12px; padding: 0; line-height: 1;
  &:hover { color: var(--red); }
}


/* 중복 곡 정리 모달 */
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
  width: 100%; max-width: 720px;
  max-height: 85vh;
  display: flex; flex-direction: column;
  padding: 20px;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
  h3 { margin: 0; }
}
.dup-empty {
  padding: 32px; text-align: center; color: var(--text-dim);
}
.dup-group-list {
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 12px;
  padding-right: 4px;
}
.dup-group {
  @include card;
  padding: 12px;
}
.dup-group-header {
  display: flex; justify-content: space-between; align-items: center;
  gap: 8px; margin-bottom: 8px;
}
.dup-group-title {
  font-size: 12px; color: var(--text-dim);
}
.dup-hide-toggle {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--text-dim); margin: 0;
  cursor: pointer;
  input { margin: 0; }
}
.dup-header-actions { display: flex; gap: 8px; align-items: center; }
.dup-song-rows { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.dup-song-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px; border-radius: 6px;
  cursor: pointer;
  &:hover { background: var(--bg-soft); }
  input { margin: 0; }
}
.dup-song-title { flex: 1; font-size: 14px; }
.dup-song-meta { font-size: 12px; color: var(--text-dim); }
.dup-legend { font-size: 11px; color: var(--text-dim); margin: 4px 0 8px; }
.dup-title-edit {
  display: flex; flex-direction: column; gap: 4px;
  margin-bottom: 10px;
  label { font-size: 12px; color: var(--text-dim); margin: 0; }
}
.dup-group-actions { display: flex; justify-content: flex-end; }

.reclean-summary {
  display: flex; flex-direction: column; gap: 6px;
  padding: 12px; margin-bottom: 12px;
  background: var(--bg-soft); border-radius: 8px;
  font-size: 13px;
}
.reclean-list {
  display: flex; flex-direction: column; gap: 4px;
  max-height: 300px; overflow-y: auto;
  font-size: 12px;
}
.reclean-row {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 6px; border-radius: 4px;
  &:hover { background: var(--bg-soft); }
}
.reclean-old { color: var(--text-dim); text-decoration: line-through; }
.reclean-arrow { color: var(--text-dim); }
.reclean-new { color: var(--accent); font-weight: 600; }

@media (max-width: 640px) {
  .section-header { flex-direction: column; align-items: flex-start; }
  .review-card { flex-direction: column; align-items: stretch; }
  .rv-video { width: 100%; }
  .rv-actions { flex-direction: row; }
  .url-row { flex-direction: column; }
}
</style>
