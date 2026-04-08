<script setup lang="ts">
definePageMeta({})
const router = useRouter()
const { api } = useApi()
const { user } = useAuth()

const form = ref({
  date: new Date().toISOString().slice(0, 10),
  service_name: '',
  author: user.value?.display_name || '',
})
const error = ref('')
const saving = ref(false)

// 로그인 유저 로드가 늦어지면 그때 채워 넣기
watch(user, (u) => {
  if (u && !form.value.author) {
    form.value.author = u.display_name || ''
  }
})

async function create() {
  error.value = ''
  if (!form.value.service_name || !form.value.author) {
    error.value = '예배명과 작성자를 입력해주세요.'
    return
  }
  saving.value = true
  try {
    const data = await api<any>('/api/contis', {
      method: 'POST',
      body: JSON.stringify(form.value),
    })
    router.push(`/conti/${data.id}`)
  } catch (e: any) {
    error.value = e?.data?.detail || e?.message || '콘티 등록에 실패했습니다.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1>새 콘티 만들기</h1>

    <div class="form">
      <label>날짜</label>
      <input v-model="form.date" type="date" class="input" />

      <label>예배명</label>
      <input v-model="form.service_name" type="text" class="input" placeholder="예: 청년예배, 주일 2부" />

      <label>작성자</label>
      <input v-model="form.author" type="text" class="input" placeholder="이름" />

      <div v-if="error" class="error">{{ error }}</div>

      <button class="btn-accent" :disabled="saving" @click="create">
        {{ saving ? '만드는 중...' : '만들기' }}
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

h1 { font-size: 24px; font-weight: 800; margin-bottom: 24px; }

.form {
  @include card;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 480px;

  label {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-dim);
  }
}

.input { @include input; }
.btn-accent { @include btn-accent; margin-top: 8px; }
.error { color: var(--red); font-size: 13px; }
</style>
