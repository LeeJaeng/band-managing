<script setup lang="ts">
  import { computed, ref } from "vue";
  
  const sessionId = ref("");
  const name = ref("");
  const part = ref("");
  
  const parts = ["Vocal", "Keys", "Guitar", "Bass", "Drums"];
  
  const creating = ref(false);
  const err = ref<string | null>(null);
  
  const canEnter = computed(() => sessionId.value.trim() && name.value.trim());
  
  function nowTag() {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  }
  
  /**
   * ✅ 방 만들기 (팀 + 세션 자동 생성)
   * - /api/teams (POST)
   * - /api/sessions (POST)
   * 생성된 세션 ID를 input에 자동으로 채움
   */
  async function createRoom() {
    creating.value = true;
    err.value = null;
  
    try {
      // 1) 팀 생성
      const team = await $fetch<{ id: string }>("/api/teams", {
        method: "POST",
        body: { name: `Test Team ${nowTag()}` },
      });
  
      // 2) 세션 생성
      const session = await $fetch<{ id: string }>("/api/sessions", {
        method: "POST",
        body: { team_id: team.id, title: `Session ${nowTag()}` },
      });
  
      sessionId.value = session.id;
    } catch (e: any) {
      err.value = e?.message ?? String(e);
    } finally {
      creating.value = false;
    }
  }
  
  async function enter() {
    const sid = sessionId.value.trim();
  
    const res = await fetch(`/api/sessions/${encodeURIComponent(sid)}/join`, {
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
  
    await navigateTo({
      path: `/session/${encodeURIComponent(sid)}`,
      query: {
        pid: p.id,
        name: p.user_name,
        part: p.part || "",
        role: p.role, // LEADER/MEMBER (Step2)
      },
    });
  }
  </script>
  
  <template>
    <main class="container">
      <h1 class="h1">Band Managing</h1>
      <p class="sub">방(세션)을 만들고, 이름/파트로 입장합니다.</p>
  
      <div class="space"></div>
  
      <section class="card">
        <!-- 방 만들기 -->
        <div class="row" style="justify-content: space-between; align-items: center">
          <div>
            <div class="label">빠른 테스트</div>
            <div class="small">버튼 한 번으로 팀+세션을 생성합니다.</div>
          </div>
  
          <button class="btn-ghost" :disabled="creating" @click="createRoom">
            {{ creating ? "생성 중..." : "방 만들기" }}
          </button>
        </div>
  
        <div class="hr"></div>
  
        <!-- Session ID -->
        <div class="label">Session ID</div>
        <input class="input" v-model="sessionId" placeholder="세션 ID" />
  
        <div class="space"></div>
  
        <!-- Name -->
        <div class="label">이름</div>
        <input class="input" v-model="name" placeholder="예: Jaeng" />
  
        <div class="space"></div>
  
        <!-- Part -->
        <div class="label">파트</div>
        <select class="input" v-model="part">
          <option value="">선택 안 함</option>
          <option v-for="p in parts" :key="p" :value="p">{{ p }}</option>
        </select>
  
        <div class="space"></div>
  
        <button class="btn-primary" :disabled="!canEnter" @click="enter">
          세션 입장
        </button>
  
        <p v-if="err" class="small" style="color: var(--danger); font-weight: 800; margin-top: 10px;">
          에러: {{ err }}
        </p>
  
        <p class="small" style="margin-top: 10px;">
          팁: 먼저 들어간 사람이 <b>LEADER</b>가 됩니다. (Step2 규칙)
        </p>
      </section>
    </main>
  </template>