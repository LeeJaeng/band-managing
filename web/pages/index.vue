<script setup lang="ts">
  import { computed, ref } from "vue";
  
  const creating = ref(false);
  const err = ref<string | null>(null);
  
  // ✅ 방 이름/파트 커스터마이징
  const roomTitle = ref("Sunday Session");
  const partsText = ref("Vocal, Keys, Guitar, Bass, Drums");
  
  const canCreate = computed(() => roomTitle.value.trim().length > 0);
  
  function parseParts(v: string): string[] {
    return v
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
      .slice(0, 30);
  }
  
  function nowTag() {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
  }
  
  async function createRoom() {
    creating.value = true;
    err.value = null;
  
    try {
      // 팀 생성
      const team = await $fetch<{ id: string }>("/api/teams", {
        method: "POST",
        body: { name: `Band Team ${nowTag()}` },
      });
  
      // 세션 생성 (✅ title + parts 포함)
      const parts = parseParts(partsText.value);
      const session = await $fetch<{ id: string }>("/api/sessions", {
        method: "POST",
        body: {
          team_id: team.id,
          title: roomTitle.value.trim(),
          parts,
        },
      });
  
      // 생성 후 join으로 이동(링크 UX)
      await navigateTo(`/join?sid=${encodeURIComponent(session.id)}`);
    } catch (e: any) {
      err.value = e?.message ?? String(e);
    } finally {
      creating.value = false;
    }
  }
  </script>
  
  <template>
    <main class="container">
      <h1 class="h1">Band Managing</h1>
      <p class="sub">방을 만들고 링크로 참여자를 초대하세요.</p>
  
      <div class="space"></div>
  
      <section class="card">
        <div class="label">방 이름</div>
        <input class="input" v-model="roomTitle" placeholder="예: 주일 2부 예배" />
  
        <div class="space"></div>
  
        <div class="label">파트 목록 (쉼표로 구분)</div>
        <input class="input" v-model="partsText" placeholder="Vocal, Keys, Guitar, Bass, Drums" />
  
        <div class="space"></div>
  
        <button class="btn-primary" :disabled="!canCreate || creating" @click="createRoom">
          {{ creating ? "생성 중..." : "방 만들기" }}
        </button>
  
        <p v-if="err" class="small" style="color: var(--danger); font-weight: 800; margin-top: 10px">
          에러: {{ err }}
        </p>
  
        <div class="small" style="margin-top: 10px">
          생성 후 자동으로 <b>Join 화면</b>으로 이동합니다.
        </div>
      </section>
    </main>
  </template>