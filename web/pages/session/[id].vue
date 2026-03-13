<script setup lang="ts">
  import { computed, onMounted, ref, watchEffect } from "vue";
  import { useRoute } from "vue-router";
  import { useWs } from "~/composables/useWs";
  import {
    clearActiveSession,
    loadActiveSession,
    saveActiveSession,
    getOverlaySeconds,
    setOverlaySeconds,
  } from "~/composables/useSessionState";
  import { copyText } from "~/composables/useClipboard";
  
  const route = useRoute();
  
  const sid = computed(() => String(route.params.id || "").trim());
  
  // query에서 내 참가자 정보
  const pid = computed(() => String(route.query.pid || "").trim());
  const myName = computed(() => String(route.query.name || "").trim());
  const myPart = computed(() => String(route.query.part || "").trim());
  const myRole = computed(() => String(route.query.role || "MEMBER").trim()); // LEADER/MEMBER
  
  const valid = ref<"loading" | "ok" | "notfound" | "error">("loading");
  const sessionInfo = ref<any>(null);
  
  const participants = ref<any[]>([]);
  const permMap = ref<Record<string, boolean>>({}); // participant_id -> can_broadcast

    // -------- Presets (Step4) --------
  const presets = ref<any[]>([]);
  const presetsLoading = ref(false);
  const presetErr = ref<string | null>(null);
  const shareMsg = ref<string | null>(null);

  const newPresetTitle = ref("");
  const newPresetText = ref("");
  const presetSaving = ref(false);

  // 수정 모드
  const editingPresetId = ref<string | null>(null);
  const editTitle = ref("");
  const editText = ref("");

  const normalizedNewPresetTitle = computed(() => newPresetTitle.value.trim());
  const normalizedNewPresetText = computed(() => newPresetText.value.trim());
  const normalizedEditTitle = computed(() => editTitle.value.trim());
  const normalizedEditText = computed(() => editText.value.trim());
  const canCreatePreset = computed(() => isLeader.value && normalizedNewPresetTitle.value.length > 0 && normalizedNewPresetTitle.value.length <= 40 && normalizedNewPresetText.value.length <= 120);
  const canUpdatePreset = computed(() => isLeader.value && !!editingPresetId.value && normalizedEditTitle.value.length > 0 && normalizedEditTitle.value.length <= 40 && normalizedEditText.value.length <= 120);
  
  // 오버레이 시간(초) - 개인 설정
  const overlaySeconds = ref<number>(4);
  onMounted(() => {
    if (process.client) overlaySeconds.value = getOverlaySeconds();
  });
  
  // ✅ 세션 존재 검증
  watchEffect(async () => {
    if (!sid.value) return;
  
    valid.value = "loading";
    sessionInfo.value = null;
  
    try {
      const data = await $fetch(`/api/sessions/${encodeURIComponent(sid.value)}`);
      sessionInfo.value = data;
      valid.value = "ok";
    } catch (e: any) {
      const status = e?.statusCode || e?.status || 0;
      if (status === 404) valid.value = "notfound";
      else valid.value = "error";
    }
  });
  
  // ✅ 참가자/권한 로드
  async function refreshMembers() {
    if (!sid.value) return;
  
    const list = await $fetch<any[]>(`/api/sessions/${encodeURIComponent(sid.value)}/participants`);
    participants.value = list;
  
    const perms = await $fetch<any[]>(`/api/sessions/${encodeURIComponent(sid.value)}/broadcast-permissions`);
    const m: Record<string, boolean> = {};
    for (const p of perms) m[p.participant_id] = !!p.can_broadcast;
    permMap.value = m;
  }
  async function refreshPresets() {
    if (!sessionInfo.value?.team_id) return;

    presetsLoading.value = true;
    presetErr.value = null;

    try {
      const list = await $fetch<any[]>(`/api/teams/${encodeURIComponent(sessionInfo.value.team_id)}/presets`);
      presets.value = Array.isArray(list) ? list : [];
    } catch (e: any) {
      presetErr.value = e?.message ?? String(e);
    } finally {
      presetsLoading.value = false;
    }
  }
  
  watchEffect(async () => {
    if (valid.value !== "ok") return;
    await refreshMembers();
    await refreshPresets();
  });
  
  // ✅ 세션 유지: (1) query가 없으면 localStorage에서 복구 (2) 정상 진입이면 저장
  onMounted(() => {
    if (!process.client) return;
  
    // query 없이 직접 들어온 케이스(새로고침/홈 복귀/주소 입력 등)
    if (!pid.value || !myName.value) {
      const s = loadActiveSession();
      if (s?.sid === sid.value && s.pid && s.name) {
        navigateTo({
          path: `/session/${encodeURIComponent(sid.value)}`,
          query: { pid: s.pid, name: s.name, part: s.part || "", role: s.role || "MEMBER" },
        });
      }
      return;
    }
  
    // 정상 진입이면 저장
    saveActiveSession({
      sid: sid.value,
      pid: pid.value,
      name: myName.value,
      part: myPart.value || "",
      role: myRole.value,
      joinedAt: Date.now(),
    });
  });
  
  // WS 연결
  const wsState = computed(() => {
    if (process.server) return null;
    if (valid.value !== "ok") return null;
    if (!sid.value || !pid.value || !myName.value) return null;
  
    return useWs(sid.value, {
      id: pid.value,
      name: myName.value,
      part: myPart.value || null,
    });
  });
  
  const connected = computed(() => wsState.value?.connected.value ?? false);
  const lastMessageAt = computed(() => wsState.value?.lastMessageAt.value ?? null);
  const events = computed(() => wsState.value?.events.value ?? []);
  
  // join 이벤트 오면 목록 갱신
  watchEffect(() => {
    const joined = events.value.find((e: any) => e?.type === "USER_JOINED");
    if (joined) setTimeout(() => refreshMembers(), 200);
  });
  
  // 권한 변경 실시간 반영(서버가 PERMISSION_UPDATED를 뿌리는 경우)
  watchEffect(() => {
    const permEvt = events.value.find((e: any) => e?.type === "PERMISSION_UPDATED") as any;
    if (!permEvt?.data) return;
    const { participant_id, can_broadcast } = permEvt.data;
    permMap.value = { ...permMap.value, [participant_id]: !!can_broadcast };
  });

  watchEffect(() => {
    const presetEvt = events.value.find((e: any) => e?.type === "PRESETS_UPDATED") as any;
    if (!presetEvt?.data?.team_id) return;
    if (presetEvt.data.team_id !== sessionInfo.value?.team_id) return;
    refreshPresets();
  });
  
  const isLeader = computed(() => myRole.value === "LEADER");
  const canBroadcast = computed(() => isLeader.value || !!permMap.value[pid.value]);
  
  // 브로드캐스트 오버레이(중앙, 반투명)
  const latestBroadcast = computed(() => events.value.find((e: any) => e?.type === "BROADCAST") as any);
  const overlayText = computed(() => latestBroadcast.value?.data?.payload?.text || "");
  const overlaySender = computed(() => latestBroadcast.value?.data?.sender || null);
  
  const overlayVisible = ref(false);
  let overlayTimer: any = null;
  
  watchEffect(() => {
    if (!overlayText.value) return;
    overlayVisible.value = true;
    if (overlayTimer) clearTimeout(overlayTimer);
    overlayTimer = setTimeout(() => (overlayVisible.value = false), overlaySeconds.value * 1000);
  });
  
  function updateOverlaySeconds(n: number) {
    overlaySeconds.value = Math.max(1, Math.min(20, Math.floor(n || 4)));
    if (process.client) setOverlaySeconds(overlaySeconds.value);
  }
  
  // ✅ 공유 링크 복사 (요구사항 6)
  async function copyShareLink() {
    const url = `${location.origin}/join?sid=${encodeURIComponent(sid.value)}`;
    const ok = await copyText(url);
    shareMsg.value = ok ? "공유 링크를 복사했습니다." : "복사에 실패했습니다. 직접 길게 눌러 복사해주세요.";
    if (overlayTimer) clearTimeout(overlayTimer);
    overlayTimer = setTimeout(() => {
      shareMsg.value = null;
    }, 1500);
  }
  
  // ✅ 나가기 (요구사항 1)
  async function leaveSession() {
    if (process.client) clearActiveSession();
    await navigateTo("/");
  }
  
  // 리더 권한 토글
  async function togglePermission(targetPid: string) {
      if (!isLeader.value) return;
      const current = !!permMap.value[targetPid];
      const next = !current;
    
      await $fetch(`/api/sessions/${encodeURIComponent(sid.value)}/broadcast-permissions`, {
        method: "POST",
        body: { participant_id: targetPid, can_broadcast: next },
      });
    
      // 내 화면 즉시 반영
      permMap.value = { ...permMap.value, [targetPid]: next };
    }
    function startEdit(p: any) {
    editingPresetId.value = p.id;
    editTitle.value = String(p.title || "");
    editText.value = String(p?.payload?.text ?? "");
  }

  function cancelEdit() {
    editingPresetId.value = null;
    editTitle.value = "";
    editText.value = "";
    presetErr.value = null;
  }

  async function createPreset() {
    if (!isLeader.value) return;
    if (!sessionInfo.value?.team_id) return;

    const title = normalizedNewPresetTitle.value;
    const text = normalizedNewPresetText.value;

    if (!title) {
      presetErr.value = "버튼명을 입력해주세요.";
      return;
    }
    if (title.length > 40) {
      presetErr.value = "버튼명은 40자 이하로 입력해주세요.";
      return;
    }
    if (text.length > 120) {
      presetErr.value = "전송 내용은 120자 이하로 입력해주세요.";
      return;
    }

    presetSaving.value = true;
    presetErr.value = null;
    try {
      await $fetch(`/api/teams/${encodeURIComponent(sessionInfo.value.team_id)}/presets`, {
        method: "POST",
        body: { team_id: sessionInfo.value.team_id, title, text: text || null },
      });

      newPresetTitle.value = "";
      newPresetText.value = "";
      await refreshPresets();
    } catch (e: any) {
      presetErr.value = e?.message ?? String(e);
    } finally {
      presetSaving.value = false;
    }
  }

  async function updatePreset() {
    if (!isLeader.value) return;
    if (!editingPresetId.value) return;

    const title = normalizedEditTitle.value;
    const text = normalizedEditText.value;

    if (!title) {
      presetErr.value = "버튼명을 입력해주세요.";
      return;
    }
    if (title.length > 40) {
      presetErr.value = "버튼명은 40자 이하로 입력해주세요.";
      return;
    }
    if (text.length > 120) {
      presetErr.value = "전송 내용은 120자 이하로 입력해주세요.";
      return;
    }

    presetSaving.value = true;
    presetErr.value = null;
    try {
      await $fetch(`/api/presets/${encodeURIComponent(editingPresetId.value)}`, {
        method: "PUT",
        body: { title, text }, // text가 ""면 서버에서 payload.text 제거하도록 되어있으면 “title 전송”이 됨
      });

      cancelEdit();
      await refreshPresets();
    } catch (e: any) {
      presetErr.value = e?.message ?? String(e);
    } finally {
      presetSaving.value = false;
    }
  }

  async function deletePreset(id: string, title?: string) {
    if (!isLeader.value) return;
    if (process.client) {
      const ok = window.confirm(`프리셋 \"${title || "이 항목"}\"을 삭제할까요?`);
      if (!ok) return;
    }

    presetSaving.value = true;
    presetErr.value = null;
    try {
      await $fetch(`/api/presets/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });

      if (editingPresetId.value === id) cancelEdit();
      await refreshPresets();
    } catch (e: any) {
      presetErr.value = e?.message ?? String(e);
    } finally {
      presetSaving.value = false;
    }
  }
  
  async function send(text: string) {
    await $fetch("/api/broadcasts", {
      method: "POST",
      body: {
        session_id: sid.value,
        sender_id: pid.value,
        target: { all: true },
        type: "TEXT",
        payload: { text: text || " " },
      },
    });
  }
  async function sendPreset(p: any) {
    const title = String(p?.title || "").trim();
    const text = String(p?.payload?.text ?? "").trim();

    // ✅ 규칙: text가 비어있으면 title 그대로 전송
    const toSend = text.length > 0 ? text : title;

    if (!toSend) return;
    await send(toSend);
  }
  </script>
  
  <template>
    <main class="container">
      <section v-if="!sid" class="card">
        <h1 class="h1">세션 ID가 없습니다</h1>
        <NuxtLink class="btn-primary" to="/">처음으로</NuxtLink>
      </section>
  
      <section v-else-if="valid === 'loading'" class="card">
        <h1 class="h1">세션 확인 중...</h1>
        <p class="sub mono">{{ sid }}</p>
      </section>
  
      <section v-else-if="valid === 'notfound'" class="card">
        <h1 class="h1">세션이 존재하지 않습니다</h1>
        <p class="sub mono">{{ sid }}</p>
        <NuxtLink class="btn-primary" to="/">처음으로</NuxtLink>
      </section>
  
      <section v-else-if="valid === 'error'" class="card">
        <h1 class="h1">세션 확인 실패</h1>
        <p class="sub mono">{{ sid }}</p>
        <button class="btn" @click="() => location.reload()">새로고침</button>
      </section>
  
      <template v-else>
        <section class="card">
          <div class="row" style="justify-content: space-between; align-items: center">
            <div>
              <div class="label">Session</div>
              <div class="mono small">{{ sid }}</div>
  
              <div class="space"></div>
  
              <div v-if="sessionInfo?.title" style="font-weight: 900">{{ sessionInfo.title }}</div>
  
              <div class="small" style="margin-top: 6px">
                Me:
                <b>{{ myName }}</b>
                <span v-if="myPart">({{ myPart }})</span>
                <span class="badge" style="margin-left: 8px">{{ myRole }}</span>
                <span class="badge" :class="canBroadcast ? 'badge-ok' : ''" style="margin-left: 8px">
                  can_broadcast: {{ canBroadcast ? "ON" : "OFF" }}
                </span>
              </div>
            </div>
  
            <div style="text-align: right">
              <span class="badge" :class="connected ? 'badge-ok' : 'badge-warn'">
                WS: {{ connected ? "Connected" : "Disconnected" }}
              </span>
              <span v-if="lastMessageAt" class="small">
                &nbsp;· last: {{ new Date(lastMessageAt).toLocaleTimeString() }}
              </span>
  
              <div class="space"></div>
  
              <div class="row" style="justify-content:flex-end;">
                <button class="btn" @click="copyShareLink">공유 링크 복사</button>
                <button class="btn-danger" @click="leaveSession">나가기</button>
              </div>
              <div v-if="shareMsg" class="small" style="margin-top: 8px;">{{ shareMsg }}</div>
            </div>
          </div>
  
          <div class="hr"></div>
  
          <div class="panel">
            <div class="label">브로드캐스트 표시 시간</div>
            <div class="row" style="align-items:center;">
              <input
                class="input"
                style="max-width: 120px;"
                type="number"
                :value="overlaySeconds"
                min="1"
                max="20"
                @input="updateOverlaySeconds(Number(($event.target as HTMLInputElement).value || 4))"
              />
              <span class="small">초 (1~20)</span>
            </div>
          </div>
  
          <div class="space"></div>
  
          <div class="panel" style="height: 44vh; display:flex; align-items:center; justify-content:center;">
            <span class="small">Score Viewer (coming soon)</span>
          </div>
  
          <div v-if="canBroadcast" class="space"></div>
  
          <div v-if="canBroadcast" class="panel">
            <div class="label">송신 패널</div>

            <div class="row" v-if="presets.length > 0">
              <button
                v-for="p in presets"
                :key="p.id"
                class="btn"
                @click="sendPreset(p)"
              >
                {{ p.title }}
              </button>
            </div>

            <div class="row" v-else>
              <button class="btn" @click="send('벌스로 갑니다')">Verse</button>
              <button class="btn" @click="send('코러스로 갑니다')">Chorus</button>
              <button class="btn" @click="send('엔딩 컷!')">Cut</button>
              <button class="btn" @click="send('찬양 변경!')">Change</button>
            </div>

            <div class="small" style="margin-top: 8px;">
              프리셋이 있으면 프리셋 버튼이 표시됩니다.
            </div>
          </div>
  
          <div v-if="isLeader" class="space"></div>
  
          <div v-if="isLeader" class="panel">
            <div class="label">권한 관리</div>
            <div class="small">멤버의 방송 권한을 ON/OFF 할 수 있습니다.</div>
            <div class="hr"></div>
  
            <div
              v-for="p in participants"
              :key="p.id"
              class="row"
              style="justify-content: space-between; align-items:center; padding: 6px 0;"
            >
              <div>
                <b>{{ p.user_name }}</b>
                <span class="small" v-if="p.part">({{ p.part }})</span>
                <span class="badge" style="margin-left: 8px">{{ p.role }}</span>
                <span v-if="p.id === pid" class="badge badge-ok" style="margin-left: 8px">ME</span>
              </div>
  
              <div class="row" style="gap:8px; align-items:center;">
                <span class="badge" :class="permMap[p.id] ? 'badge-ok' : ''">
                  {{ permMap[p.id] ? "ON" : "OFF" }}
                </span>
  
                <button v-if="p.role !== 'LEADER'" class="btn" @click="togglePermission(p.id)">
                  {{ permMap[p.id] ? "권한 OFF" : "권한 ON" }}
                </button>
              </div>
            </div>
          </div>
          <div v-if="isLeader" class="panel" style="margin-top: 12px;">
            <div class="label">프리셋 관리 (리더 전용)</div>

            <p v-if="presetErr" class="small" style="color: var(--danger); font-weight: 800;">
              {{ presetErr }}
            </p>

            <div class="hr"></div>

            <!-- Create -->
            <div class="label">새 프리셋 추가</div>
            <div class="row">
              <input class="input" style="flex:1; min-width: 180px;" v-model="newPresetTitle" maxlength="40" placeholder="버튼명(title)" />
              <input class="input" style="flex:2; min-width: 240px;" v-model="newPresetText" maxlength="120" placeholder="전송 내용(text, 비우면 title 전송)" />
              <button class="btn-primary" :disabled="presetsLoading || presetSaving || !canCreatePreset" @click="createPreset">
                {{ presetSaving ? "저장 중..." : "추가" }}
              </button>
            </div>
            <p class="small" style="margin-top: 6px;">
              버튼명 40자 / 전송 내용 120자까지 입력할 수 있습니다.
            </p>

            <div class="hr"></div>

            <!-- List -->
            <div class="label">프리셋 목록</div>

            <div v-if="presets.length === 0" class="small">
              아직 프리셋이 없습니다. 위에서 추가하세요.
            </div>

            <div v-for="p in presets" :key="p.id" class="panel" style="margin-top: 10px;">
              <div class="row" style="justify-content: space-between; align-items: center;">
                <div>
                  <b>{{ p.title }}</b>
                  <div class="small" style="margin-top: 4px;">
                    text: <span class="mono">{{ p?.payload?.text ?? "(없음 → title 전송)" }}</span>
                  </div>
                </div>

                <div class="row">
                  <button class="btn" :disabled="presetSaving" @click="startEdit(p)">수정</button>
                  <button class="btn-danger" :disabled="presetSaving" @click="deletePreset(p.id, p.title)">삭제</button>
                </div>
              </div>

              <!-- Edit -->
              <div v-if="editingPresetId === p.id" class="hr"></div>
              <div v-if="editingPresetId === p.id">
                <div class="label">수정</div>
                <div class="row">
                  <input class="input" style="flex:1; min-width: 180px;" v-model="editTitle" maxlength="40" placeholder="버튼명(title)" />
                  <input class="input" style="flex:2; min-width: 240px;" v-model="editText" maxlength="120" placeholder="전송 내용(text, 비우면 title 전송)" />
                  <button class="btn-primary" :disabled="presetSaving || !canUpdatePreset" @click="updatePreset">
                    {{ presetSaving ? "저장 중..." : "저장" }}
                  </button>
                  <button class="btn" :disabled="presetSaving" @click="cancelEdit">취소</button>
                </div>
                <p class="small" style="margin-top: 6px;">
                  text를 빈 값으로 저장하면 “title 전송” 규칙이 적용됩니다.
                </p>
              </div>
            </div>
          </div>

        </section>
  
        <div class="space"></div>
  
        <section class="card">
          <div class="label">Recent events</div>
          <pre class="panel mono" style="max-height: 220px; overflow:auto;">{{ events.slice(0, 8) }}</pre>
        </section>
  
        <!-- 중앙 반투명 오버레이 -->
        <div
          v-if="overlayVisible && overlayText"
          style="
            position: fixed;
            inset: 0;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 16px;
            pointer-events: none;
          "
        >
          <div
            style="
              width: min(720px, calc(100vw - 24px));
              border-radius: 18px;
              border: 1px solid rgba(232,238,246,0.18);
              background: rgba(18, 27, 38, 0.22);
              box-shadow: 0 6px 18px rgba(0,0,0,.18);
              padding: 18px 18px;
            "
          >
            <div style="font-size: 13px; opacity: .85;">
              From:
              <b>{{ overlaySender?.name || "Unknown" }}</b>
              <span v-if="overlaySender?.part" style="opacity:.85;">({{ overlaySender.part }})</span>
            </div>
  
            <div style="margin-top: 10px; font-size: 34px; font-weight: 900; letter-spacing: -0.4px; line-height: 1.15;">
              {{ overlayText }}
            </div>
          </div>
        </div>
      </template>
    </main>
  </template>