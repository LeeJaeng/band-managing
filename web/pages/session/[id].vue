<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watchEffect } from "vue";
  import { useRoute } from "vue-router";
  import { useWs } from "~/composables/useWs";
  
  const route = useRoute();
  
  const sid = computed(() => String(route.params.id || "").trim());
  const role = computed(() => (route.query.role === "leader" ? "leader" : "member") as "leader" | "member");
  
  const valid = ref<"loading" | "ok" | "notfound" | "error">("loading");
  const sessionInfo = ref<any>(null);
  
  // ✅ 세션 존재 검증 (sid 없으면 아예 진행 X)
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
  
  // ✅ WS는 세션 ok + client에서만
  const wsState = computed(() => {
    if (process.server) return null;
    if (valid.value !== "ok") return null;
    if (!sid.value) return null;
    return useWs(sid.value);
  });
  
  const connected = computed(() => wsState.value?.connected.value ?? false);
  const lastMessageAt = computed(() => wsState.value?.lastMessageAt.value ?? null);
  const events = computed(() => wsState.value?.events.value ?? []);
  
  const latestBroadcast = computed(() => {
    return events.value.find((e: any) => e?.type === "BROADCAST") as any;
  });
  
  const overlayText = computed(() => latestBroadcast.value?.data?.payload?.text || "");
  const overlaySender = computed(() => latestBroadcast.value?.data?.sender_name || "");
  const overlayTarget = computed(() => latestBroadcast.value?.data?.target || null);
  
  const overlayOpen = ref(true);
  watchEffect(() => {
    // 새 브로드캐스트가 오면 다시 열어줌
    if (overlayText.value) overlayOpen.value = true;
  });
  
  async function send(text: string) {
    await $fetch("/api/broadcasts", {
      method: "POST",
      body: {
        session_id: sid.value,
        sender_name: "Leader",
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
        <p class="sub">올바른 링크로 접속해 주세요.</p>
        <div class="space"></div>
        <NuxtLink class="btn-primary" to="/">처음으로</NuxtLink>
      </section>
  
      <section v-else-if="valid === 'loading'" class="card">
        <h1 class="h1">세션 확인 중...</h1>
        <p class="sub mono">{{ sid }}</p>
      </section>
  
      <section v-else-if="valid === 'notfound'" class="card">
        <h1 class="h1">세션이 존재하지 않습니다</h1>
        <p class="sub">세션 ID가 잘못되었거나 종료된 세션일 수 있습니다.</p>
        <div class="space"></div>
        <div class="panel mono">{{ sid }}</div>
        <div class="space"></div>
        <NuxtLink class="btn-primary" to="/">처음으로</NuxtLink>
      </section>
  
      <section v-else-if="valid === 'error'" class="card">
        <h1 class="h1">세션 확인 실패</h1>
        <p class="sub">네트워크/서버 문제일 수 있습니다.</p>
        <div class="space"></div>
        <div class="panel mono">{{ sid }}</div>
        <div class="space"></div>
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
            </div>
  
            <div style="text-align: right">
              <div class="small">Mode: <b>{{ role }}</b></div>
              <div class="space"></div>
              <span class="badge" :class="connected ? 'badge-ok' : 'badge-warn'">
                WS: {{ connected ? "Connected" : "Disconnected" }}
              </span>
              <span v-if="lastMessageAt" class="small">
                &nbsp;· last: {{ new Date(lastMessageAt).toLocaleTimeString() }}
              </span>
            </div>
          </div>
  
          <div class="hr"></div>
  
          <div class="panel" style="height: 52vh; display:flex; align-items:center; justify-content:center;">
            <span class="small">Score Viewer (coming soon)</span>
          </div>
  
          <div v-if="role === 'leader'" class="space"></div>
  
          <!-- Leader Panel -->
          <div v-if="role === 'leader'" class="panel">
            <div class="label">Leader Panel</div>
            <div class="row">
              <button class="btn" @click="send('벌스로 갑니다')">Verse</button>
              <button class="btn" @click="send('코러스로 갑니다')">Chorus</button>
              <button class="btn" @click="send('엔딩 컷!')">Cut</button>
              <button class="btn" @click="send('찬양 변경!')">Change</button>
            </div>
            <p class="small" style="margin-top: 10px">
              다른 창에서 Member로 들어가 오버레이가 뜨는지 확인하세요.
            </p>
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
        <div v-if="overlayText && overlayOpen" style="position: fixed; inset: 0; z-index: 9999; display:flex; align-items:center; justify-content:center; padding: 16px; background: rgba(0,0,0,.72);">
          <div class="card" style="max-width: 720px; width: 100%;">
            <div class="small">From: <b>{{ overlaySender }}</b></div>
            <div class="space"></div>
            <div style="font-size: 28px; font-weight: 900; letter-spacing: -0.3px; word-break: break-word;">
              {{ overlayText }}
            </div>
            <div class="space"></div>
            <div class="small">Target: <span class="mono">{{ overlayTarget }}</span></div>
            <div class="space"></div>
            <div class="row" style="justify-content:flex-end;">
              <button class="btn-primary" @click="overlayOpen = false">확인</button>
            </div>
          </div>
        </div>
      </template>
    </main>
  </template>