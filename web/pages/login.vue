<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { login, isLoggedIn } = useAuth()

const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

// 이미 로그인 상태면 홈으로
if (isLoggedIn.value) {
  navigateTo('/')
}

async function handleLogin() {
  error.value = ''
  if (!form.value.username || !form.value.password) {
    error.value = '아이디와 비밀번호를 입력해주세요.'
    return
  }

  loading.value = true
  try {
    await login(form.value.username, form.value.password)
    navigateTo('/')
  } catch (e: any) {
    error.value = e?.data?.detail || e?.message || '로그인 실패'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>Band Managing</h1>
      <p class="subtitle">찬양팀 운영 관리</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <label>아이디</label>
        <input
          v-model="form.username"
          class="input"
          placeholder="아이디"
          autocomplete="username"
        />

        <label>비밀번호</label>
        <input
          v-model="form.password"
          type="password"
          class="input"
          placeholder="비밀번호"
          autocomplete="current-password"
        />

        <div v-if="error" class="error">{{ error }}</div>

        <button type="submit" class="btn-accent" :disabled="loading">
          {{ loading ? '로그인 중...' : '로그인' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.login-card {
  @include card;
  padding: 32px;
  width: 100%;
  max-width: 360px;

  h1 {
    font-size: 22px;
    font-weight: 800;
    margin: 0 0 4px;
    text-align: center;
  }

  .subtitle {
    text-align: center;
    color: var(--text-dim);
    font-size: 14px;
    margin: 0 0 24px;
  }
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 8px;

  label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-dim);
    margin-top: 4px;
  }
}

.input { @include input; }
.btn-accent {
  @include btn-accent;
  margin-top: 12px;
}

.error {
  color: var(--red);
  font-size: 13px;
  text-align: center;
}
</style>
