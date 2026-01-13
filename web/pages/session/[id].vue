<script setup lang="ts">
  import { computed, ref, watchEffect } from "vue";
  import { useRoute } from "vue-router";
  import { useWs } from "~/composables/useWs";
  
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
  
  // 세션 존재 검증
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
  
  // 참가자 목록 + 권한 맵 로드
  async function refreshMembers() {
    if (!sid.value) return;
    const list = await $fetch<any[]>(`/api/sessions/${encodeURIComponent(sid.value)}/participants`);
    participants.value = list;
  
    const perms = await $fetch<any[]>(`/api/sessions/${encodeURIComponent(sid.value)}/broadcast-permissions`);
    const m: Record<string, boolean> = {};
    for (const p of perms) m[p.participant_id] = !!p.can_broadcast;
    permMap.value = m;
  }
  
  watchEffect(async () => {
    if (valid.value !== "ok") return;
    await refreshMembers();
  });
  
  // WS (세션 ok + client + 내 pid/name 준비)
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
  
  const latestBroadcast = computed(() => events.value.find((e: any) => e?.type === "BROADCAST") as any);
  const overlayText = computed(() => latestBroadcast.value?.data?.payload?.text || "");
  const overlaySender = computed(() => latestBroadcast.value?.data?.sender || null);
  const overlayOpen = ref(true);
  
  watchEffect(() => {
    if (overlayText.value) overlayOpen.value = true;
  });
  
  // WS에서 누군가 join 했으면 멤버 목록 갱신
  watchEffect(() => {
    const joined = events.value.find((e: any) => e?.type === "USER_JOINED");
    if (joined) {
      // 너무 자주 갱신하지 않게 한 틱 뒤 갱신
      setTimeout(() => refreshMembers(), 200);
    }
  });
  
  // LEADER 권한 토글
  const isLeader = computed(() => myRole.value === "LEADER");
  
  async function togglePermission(targetPid: string) {
    if (!isLeader.value) return;
    const current = !!permMap.value[targetPid];
    const next = !current;
  
    await $fetch(`/api/sessions/${encodeURIComponent(sid.value)}/broadcast-permissions`, {
      method: "POST",
      body: { participant_id: targetPid, can_broadcast: next },
    });
  
    permMap.value = { ...permMap.value, [targetPid]: next };
  }
  
  async function send(text: string) {
    await $fetch("/api/broadcasts", {
      method: "POST",
      body: {
        session_id: sid.value,
        sender_id: pid.value, // Step2
        target: { all: true },
        type: "TEXT",
        payload: { text },
      },
    });
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
        <!-- Header -->
        <section class="card">
          <div class="row" style="justify-content: space-between; align-items: center">
            <div>
              <div class="label">Session</div>
              <div class="mono small">{{ sid }}</div>
              <div class="space"></div>
              <div v-if="sessionInfo?.title" style="font-weight: 900">{{ sessionInfo.title }}</div>
              <div class="small" style="margin-top: 6px">
                Me: <b>{{ myName }}</b> <span v-if="myPart">({{ myPart }})</span>
                <span class="badge" style="margin-left: 8px">{{ myRole }}</span>
              </div>
            </div>
  
            <div style="text-align: right">
              <span class="badge" :class="connected ? 'badge-ok' : 'badge-warn'">
                WS: {{ connected ? "Connected" : "Disconnected" }}
              </span>
              <span v-if="lastMessageAt" class="small">
                &nbsp;· last: {{ new Date(lastMessageAt).toLocaleTimeString() }}
              </span>
            </div>
          </div>
  
          <div class="hr"></div>
  
          <div class="panel" style="height: 46vh; display:flex; align-items:center; justify-content:center;">
            <span class="small">Score Viewer (coming soon)</span>
          </div>
  
          <div v-if="isLeader" class="space"></div>
  
          <!-- Leader Panel -->
          <div v-if="isLeader" class="panel">
            <div class="label">Leader Panel</div>
            <div class="row">
              <button class="btn" @click="send('벌스로 갑니다')">Verse</button>
              <button class="btn" @click="send('코러스로 갑니다')">Chorus</button>
              <button class="btn" @click="send('엔딩 컷!')">Cut</button>
              <button class="btn" @click="send('찬양 변경!')">Change</button>
            </div>
            <p class="small" style="margin-top: 10px">
              멤버 권한을 토글해서 “임시 방송권한”을 부여할 수 있습니다.
            </p>
          </div>
        </section>
  
        <div class="space"></div>
  
        <!-- Participants -->
        <section class="card">
          <div class="label">Participants</div>
          <div class="panel">
            <div v-if="participants.length === 0" class="small">참여자가 없습니다.</div>
            <div v-for="p in participants" :key="p.id" class="row" style="justify-content: space-between; align-items:center; padding: 8px 0;">
              <div>
                <b>{{ p.user_name }}</b>
                <span class="small" v-if="p.part">({{ p.part }})</span>
                <span class="badge" style="margin-left: 8px">{{ p.role }}</span>
                <span v-if="p.id === pid" class="badge badge-ok" style="margin-left: 8px">ME</span>
              </div>
  
              <div class="row" style="gap:8px; align-items:center;">
                <span class="badge" :class="permMap[p.id] ? 'badge-ok' : ''">
                  can_broadcast: {{ permMap[p.id] ? "ON" : "OFF" }}
                </span>
  
                <button
                  v-if="isLeader && p.role !== 'LEADER'"
                  class="btn"
                  @click="togglePermission(p.id)"
                >
                  {{ permMap[p.id] ? "권한 OFF" : "권한 ON" }}
                </button>
              </div>
            </div>
          </div>
        </section>
  
        <div class="space"></div>
  
        <!-- Events -->
        <section class="card">
          <div class="label">Recent events</div>
          <pre class="panel mono" style="max-height: 220px; overflow:auto;">
  {{ events.slice(0, 8) }}
          </pre>
        </section>
  
        <!-- Broadcast Overlay -->
        <div
          v-if="overlayText && overlayOpen"
          style="position: fixed; inset: 0; z-index: 9999; display:flex; align-items:center; justify-content:center; padding: 16px; background: rgba(0,0,0,.72);"
        >
          <div class="card" style="max-width: 720px; width: 100%;">
            <div class="small">
              From:
              <b>{{ overlaySender?.name || "Unknown" }}</b>
              <span class="small" v-if="overlaySender?.part">({{ overlaySender.part }})</span>
              <span class="badge" style="margin-left: 8px" v-if="overlaySender?.role">
                {{ overlaySender.role }}
              </span>
            </div>
  
            <div class="space"></div>
  
            <div style="font-size: 28px; font-weight: 900; letter-spacing: -0.3px; word-break: break-word;">
              {{ overlayText }}
            </div>
  
            <div class="space"></div>
  
            <div class="row" style="justify-content:flex-end;">
              <button class="btn-primary" @click="overlayOpen = false">확인</button>
            </div>
          </div>
        </div>
      </template>
    </main>
  </template>