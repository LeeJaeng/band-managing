<script setup lang="ts">
const router = useRouter()
const { api } = useApi()

const form = ref({
  date: new Date().toISOString().slice(0, 10),
  service_name: '',
  author: '',
})
const error = ref('')

async function create() {
  if (!form.value.service_name || !form.value.author) {
    error.value = '예배명과 작성자를 입력해주세요.'
    return
  }
  const data = await api<any>('/api/contis', {
    method: 'POST',
    body: JSON.stringify(form.value),
  })
  router.push(`/conti/${data.id}`)
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

      <button class="btn-accent" @click="create">만들기</button>
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
