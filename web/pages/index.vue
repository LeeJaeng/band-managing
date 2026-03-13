<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { clearActiveSession, loadActiveSession, type StoredSession } from "~/composables/useSessionState";
import { copyText } from "~/composables/useClipboard";

const creating = ref(false);
const err = ref<string | null>(null);
const copyMsg = ref<string | null>(null);
const activeSession = ref<StoredSession | null>(null);

const roomTitle = ref("Sunday Session");
const partInput = ref("");
const DEFAULT_PARTS = ["보컬", "피아노", "신디", "기타", "베이스", "드럼", "리더", "설교자", "음향", "영상"];
const customParts = ref<string[]>([...DEFAULT_PARTS]);

const canCreate = computed(() => roomTitle.value.trim().length > 0);
const canAddPart = computed(() => partInput.value.trim().length > 0 && customParts.value.length < 30);
const shareLink = computed(() => {
  if (!activeSession.value || !process.client) return "";
  return `${location.origin}/join?sid=${encodeURIComponent(activeSession.value.sid)}`;
});

onMounted(() => {
  if (!process.client) return;
  activeSession.value = loadActiveSession();
});

function normalizedParts(): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of customParts.value) {
    const v = raw.trim();
    if (!v) continue;
    const key = v.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(v);
  }
  return result.slice(0, 30);
}

function addPart() {
  const v = partInput.value.trim();
  if (!v) return;
  if (customParts.value.some((p) => p.trim().toLowerCase() === v.toLowerCase())) {
    partInput.value = "";
    return;
  }
  if (customParts.value.length >= 30) return;
  customParts.value = [...customParts.value, v];
  partInput.value = "";
}

function removePart(idx: number) {
  customParts.value = customParts.value.filter((_, i) => i !== idx);
}

function resetParts() {
  customParts.value = [...DEFAULT_PARTS];
  partInput.value = "";
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
    const team = await $fetch<{ id: string }>("/api/teams", {
      method: "POST",
      body: { name: `Band Team ${nowTag()}` },
    });

    const session = await $fetch<{ id: string }>("/api/sessions", {
      method: "POST",
      body: {
        team_id: team.id,
        title: roomTitle.value.trim(),
        parts: normalizedParts(),
      },
    });

    await navigateTo(`/join?sid=${encodeURIComponent(session.id)}`);
  } catch (e: any) {
    err.value = e?.message ?? String(e);
  } finally {
    creating.value = false;
  }
}

async function resumeSession() {
  if (!activeSession.value) return;
  await navigateTo({
    path: `/session/${encodeURIComponent(activeSession.value.sid)}`,
    query: {
      pid: activeSession.value.pid,
      name: activeSession.value.name,
      part: activeSession.value.part || "",
      role: activeSession.value.role || "MEMBER",
    },
  });
}

function leaveStoredSession() {
  clearActiveSession();
  activeSession.value = null;
  copyMsg.value = null;
}

async function copyActiveShareLink() {
  if (!shareLink.value || !process.client) return;
  const ok = await copyText(shareLink.value);
  copyMsg.value = ok ? "공유 링크를 복사했습니다." : "복사에 실패했습니다. 직접 길게 눌러 복사해주세요.";
  setTimeout(() => {
    copyMsg.value = null;
  }, 1800);
}
</script>

<template>
  <main class="container">
    <h1 class="h1">Band Managing</h1>
    <p class="sub">방을 만들고 링크로 참여자를 초대하세요.</p>

    <div class="space"></div>

    <section v-if="activeSession" class="card">
      <div class="row" style="justify-content: space-between; align-items: center">
        <div>
          <div class="label">현재 참여 중인 세션</div>
          <div class="mono small">{{ activeSession.sid }}</div>
          <div class="small" style="margin-top: 6px">
            <b>{{ activeSession.name }}</b>
            <span v-if="activeSession.part">({{ activeSession.part }})</span>
            <span class="badge" style="margin-left: 8px">{{ activeSession.role || "MEMBER" }}</span>
          </div>
        </div>

        <div class="row" style="justify-content: flex-end">
          <button class="btn-primary" @click="resumeSession">세션으로 돌아가기</button>
          <button class="btn" @click="copyActiveShareLink">공유 링크 복사</button>
          <button class="btn-danger" @click="leaveStoredSession">나가기</button>
        </div>
      </div>

      <p v-if="copyMsg" class="small" style="margin-top: 10px">{{ copyMsg }}</p>
    </section>

    <div class="space"></div>

    <section class="card">
      <div class="label">방 이름</div>
      <input class="input" v-model="roomTitle" placeholder="예: 주일 2부 예배" />

      <div class="space"></div>

      <div class="row" style="justify-content: space-between; align-items: center">
        <div class="label" style="margin-bottom: 0">파트 목록</div>
        <button class="btn-ghost" type="button" @click="resetParts">기본값 복원</button>
      </div>

      <div class="space"></div>

      <div class="row">
        <span v-for="(part, idx) in customParts" :key="`${part}-${idx}`" class="badge" style="gap: 8px">
          {{ part }}
          <button
            type="button"
            style="all: unset; cursor: pointer; font-weight: 900; opacity: 0.8"
            aria-label="파트 삭제"
            @click="removePart(idx)"
          >
            ×
          </button>
        </span>
      </div>

      <div class="space"></div>

      <div class="row">
        <input
          class="input"
          style="flex: 1; min-width: 220px"
          v-model="partInput"
          placeholder="파트 추가 예: Synth"
          @keydown.enter.prevent="addPart"
        />
        <button class="btn" type="button" :disabled="!canAddPart" @click="addPart">파트 추가</button>
      </div>

      <div class="small" style="margin-top: 10px">
        세션 생성 시 이 파트 목록이 join 화면과 세션 화면에 반영됩니다.
      </div>

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
