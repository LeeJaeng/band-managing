<script setup lang="ts">
  import { computed, onMounted, ref, watchEffect } from "vue";
  import { useRoute } from "vue-router";
  import { saveActiveSession } from "~/composables/useSessionState";
  
  const route = useRoute();
  
  const sid = ref("");
  const name = ref("");
  const part = ref("");
  
  const parts = ref<string[]>(["Vocal", "Keys", "Guitar", "Bass", "Drums"]);
  const sessionTitle = ref<string>("");
  
  const err = ref<string | null>(null);
  const joining = ref(false);
  
  const canJoin = computed(() => sid.value.trim() && name.value.trim());
  
  onMounted(() => {
    sid.value = String(route.query.sid || "").trim();
  });
  
  watchEffect(async () => {
    if (!sid.value) return;
    try {
      const s = await $fetch<any>(`/api/sessions/${encodeURIComponent(sid.value)}`);
      sessionTitle.value = s?.title || "";
      if (Array.isArray(s?.parts) && s.parts.length > 0) {
        parts.value = s.parts;
      }
    } catch {
      // ignore (입장 시 처리)
    }
  });
  
  async function join() {
    if (!canJoin.value) return;
    joining.value = true;
    err.value = null;
  
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(sid.value.trim())}/join`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_name: name.value,
          part: part.value || null,
        }),
      });
  
      if (!res.ok) {
        err.value = "세션 입장 실패";
        return;
      }
  
      const data = await res.json();
      const p = data.participant;
  
      saveActiveSession({
        sid: sid.value.trim(),
        pid: p.id,
        name: p.user_name,
        part: p.part || "",
        role: p.role,
        joinedAt: Date.now(),
      });
  
      await navigateTo({
        path: `/session/${encodeURIComponent(sid.value.trim())}`,
        query: {
          pid: p.id,
          name: p.user_name,
          part: p.part || "",
          role: p.role,
        },
      });
    } finally {
      joining.value = false;
    }
  }
  </script>
  
  <template>
    <main class="container">
      <h1 class="h1">Join Session</h1>
      <p class="sub" v-if="sessionTitle">방: <b>{{ sessionTitle }}</b></p>
      <p class="sub" v-else>이름/파트를 입력하고 세션에 입장합니다.</p>
  
      <div class="space"></div>
  
      <section class="card">
        <div class="label">Session ID</div>
        <input class="input" v-model="sid" placeholder="세션 ID" />
  
        <div class="space"></div>
  
        <div class="label">이름</div>
        <input class="input" v-model="name" placeholder="예: Jaeng" />
  
        <div class="space"></div>
  
        <div class="label">파트</div>
        <select class="input" v-model="part">
          <option value="">선택 안 함</option>
          <option v-for="p in parts" :key="p" :value="p">{{ p }}</option>
        </select>
  
        <div class="space"></div>
  
        <button class="btn-primary" :disabled="!canJoin || joining" @click="join">
          {{ joining ? "입장 중..." : "세션 입장" }}
        </button>
  
        <p v-if="err" class="small" style="color: var(--danger); font-weight: 800; margin-top: 10px">
          {{ err }}
        </p>
  
        <div class="space"></div>
  
        <NuxtLink class="btn" to="/">처음으로</NuxtLink>
      </section>
    </main>
  </template>