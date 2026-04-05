<script setup lang="ts">
definePageMeta({ layout: 'share' })

const { register, isLoggedIn } = useAuth()

const form = ref({ username: '', password: '', passwordConfirm: '', displayName: '' })
const error = ref('')
const loading = ref(false)

if (isLoggedIn.value) {
  navigateTo('/')
}

async function handleRegister() {
  error.value = ''

  if (!form.value.username || !form.value.password || !form.value.displayName) {
    error.value = '모든 항목을 입력해주세요.'
    return
  }
  if (form.value.username.length < 3) {
    error.value = '아이디는 3자 이상이어야 합니다.'
    return
  }
  if (form.value.password.length < 4) {
    error.value = '비밀번호는 4자 이상이어야 합니다.'
    return
  }
  if (form.value.password !== form.value.passwordConfirm) {
    error.value = '비밀번호가 일치하지 않습니다.'
    return
  }

  loading.value = true
  try {
    await register(form.value.username, form.value.password, form.value.displayName)
    navigateTo('/')
  } catch (e: any) {
    error.value = e?.data?.detail || e?.message || '회원가입 실패'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <h1>회원가입</h1>
      <p class="subtitle">Band Managing</p>

      <form @submit.prevent="handleRegister" class="register-form">
        <label>이름</label>
        <input v-model="form.displayName" class="input" placeholder="표시될 이름" />

        <label>아이디</label>
        <input v-model="form.username" class="input" placeholder="3자 이상" autocomplete="username" />

        <label>비밀번호</label>
        <input v-model="form.password" type="password" class="input" placeholder="4자 이상" autocomplete="new-password" />

        <label>비밀번호 확인</label>
        <input v-model="form.passwordConfirm" type="password" class="input" placeholder="비밀번호 재입력" autocomplete="new-password" />

        <div v-if="error" class="error">{{ error }}</div>

        <button type="submit" class="btn-accent" :disabled="loading">
          {{ loading ? '가입 중...' : '가입하기' }}
        </button>
      </form>

      <div class="login-link">
        이미 계정이 있으신가요? <NuxtLink to="/login">로그인</NuxtLink>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/scss/mixins' as *;

.register-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.register-card {
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

.register-form {
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
.btn-accent { @include btn-accent; margin-top: 12px; }

.error {
  color: var(--red);
  font-size: 13px;
  text-align: center;
}

.login-link {
  text-align: center;
  font-size: 13px;
  color: var(--text-dim);
  margin-top: 16px;

  a { color: var(--accent); font-weight: 600; &:hover { text-decoration: underline; } }
}
</style>
