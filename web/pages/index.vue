<script setup lang="ts">
  import { computed, ref } from "vue";
  
  const sessionId = ref("");
  const name = ref("");
  const part = ref("");
  
  const parts = ["Vocal", "Keys", "Guitar", "Bass", "Drums"];
  
  const canEnter = computed(() => sessionId.value.trim() && name.value.trim());
  
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
      alert("세션 입장 실패");
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
        role: p.role, // LEADER/MEMBER
      },
    });
  }
  </script>
  
  <template>
    <main class="container">
      <h1 class="h1">Band Managing</h1>
      <p class="sub">세션에 참여하세요</p>
  
      <div class="space"></div>
  
      <section class="card">
        <div class="label">Session ID</div>
        <input class="input" v-model="sessionId" placeholder="세션 ID" />
  
        <div class="space"></div>
  
        <div class="label">이름</div>
        <input class="input" v-model="name" placeholder="이름" />
  
        <div class="space"></div>
  
        <div class="label">파트</div>
        <select class="input" v-model="part">
          <option value="">선택 안 함</option>
          <option v-for="p in parts" :key="p" :value="p">{{ p }}</option>
        </select>
  
        <div class="space"></div>
  
        <button class="btn-primary" :disabled="!canEnter" @click="enter">
          세션 입장
        </button>
      </section>
    </main>
  </template>