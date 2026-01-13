<script setup lang="ts">
  import { computed, ref } from "vue";
  
  const sessionId = ref("");
  const role = ref<"member" | "leader">("member");
  const creating = ref(false);
  const err = ref<string | null>(null);
  const created = ref<string | null>(null);
  
  const raw = computed(() => sessionId.value.trim());
  const canEnter = computed(() => raw.value.length > 0);
  
  const enterTo = computed(() =>
    canEnter.value ? `/session/${encodeURIComponent(raw.value)}?role=${role.value}` : "#"
  );
  
  async function createSessionCode() {
    creating.value = true;
    err.value = null;
    created.value = null;
  
    try {
      // 1) 팀 생성
      const team = await $fetch<{ id: string }>("/api/teams", {
        method: "POST",
        body: { name: "UI Test Team" },
      });
  
      // 2) 세션 생성
      const session = await $fetch<{ id: string }>("/api/sessions", {
        method: "POST",
        body: { team_id: team.id, title: "UI Test Session" },
      });
  
      // 3) Leader 권한 부여
      await $fetch("/api/grants", {
        method: "POST",
        body: { session_id: session.id, user_name: "Leader", can_broadcast: true },
      });
  
      sessionId.value = session.id;
      created.value = session.id;
  
      // 4) 자동으로 리더로 입장
      await navigateTo(`/session/${encodeURIComponent(session.id)}?role=leader`);
    } catch (e: any) {
      err.value = e?.message ?? String(e);
    } finally {
      creating.value = false;
    }
  }
  
  async function copyCode() {
    if (!created.value) return;
    await navigator.clipboard.writeText(created.value);
  }
  </script>
  
  <template>
    <main class="container">
      <h1 class="h1">Band Managing</h1>
      <p class="sub">세션 ID로 입장하거나, 버튼으로 테스트 세션코드를 생성할 수 있습니다.</p>
  
      <div class="space"></div>
  
      <section class="card">
        <div class="label">Session ID</div>
        <input
          class="input"
          v-model="sessionId"
          placeholder="예: 40be22c7-..."
          autocapitalize="off"
          autocomplete="off"
          spellcheck="false"
        />
  
        <div class="space"></div>
  
        <div class="label">Mode</div>
        <div class="row">
          <button class="btn" :class="{ 'btn-primary': role === 'member' }" @click="role = 'member'">
            Team Member
          </button>
          <button class="btn" :class="{ 'btn-primary': role === 'leader' }" @click="role = 'leader'">
            Leader
          </button>
  
          <button class="btn-ghost" :disabled="creating" @click="createSessionCode">
            {{ creating ? "세션 생성 중..." : "세션코드 생성(테스트)" }}
          </button>
  
          <button class="btn" v-if="created" @click="copyCode">코드 복사</button>
        </div>
  
        <div class="hr"></div>
  
        <NuxtLink
          class="btn-primary"
          :to="enterTo"
          :style="canEnter ? '' : 'opacity:.55;pointer-events:none;'"
        >
          Enter
        </NuxtLink>
  
        <div class="space"></div>
  
        <p v-if="err" class="small" style="color: var(--danger); font-weight: 800">에러: {{ err }}</p>
  
        <p v-if="created" class="small">
          생성됨:
          <span class="mono">{{ created }}</span>
        </p>
      </section>
  
      <div class="space"></div>
  
      <section class="panel">
        <div class="label">팁</div>
        <div class="small">
          새 창(또는 시크릿)에서 같은 세션 ID로 <span class="kbd">Member</span>로 입장한 뒤,
          <span class="kbd">Leader</span>에서 버튼을 눌러 브로드캐스트가 뜨는지 확인하세요.
        </div>
      </section>
    </main>
  </template>