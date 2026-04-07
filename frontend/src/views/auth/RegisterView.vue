<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Logo区域 -->
      <div class="auth-brand">
        <div class="brand-icon">
          <el-icon :size="32"><ChatRound /></el-icon>
        </div>
        <h1 class="brand-title">创建账号</h1>
        <p class="brand-subtitle">开始您的 AI 之旅</p>
      </div>

      <!-- 注册表单 -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        size="large"
        @submit.prevent="handleSubmit"
        class="auth-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="邮箱地址"
            :prefix-icon="Message"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码（至少6位）"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="确认密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="submit-btn"
            native-type="submit"
          >
            创建账号
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 底部链接 -->
      <div class="auth-footer">
        <span>已有账号？</span>
        <router-link to="/login" class="link link-primary">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message, ChatRound } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    const result = await authStore.register({
      username: form.username,
      email: form.email,
      password: form.password
    })
    if (result.success) {
      ElMessage.success('注册成功，请登录')
      router.push('/login')
    } else {
      ElMessage.error(result.message || '注册失败')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #FAFBFE 0%, #F3F1FF 25%, #EDE9FE 50%, #F3F1FF 75%, #EEEDF9 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 80%;
    height: 150%;
    background: radial-gradient(ellipse, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
    pointer-events: none;
  }

  &::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: -10%;
    width: 60%;
    height: 100%;
    background: radial-gradient(ellipse, rgba(139, 92, 246, 0.06) 0%, transparent 70%);
    pointer-events: none;
  }
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  padding: 40px 36px;
  box-shadow: 0 8px 40px rgba(99, 102, 241, 0.15), 0 2px 8px rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.1);
  backdrop-filter: blur(10px);
  position: relative;
  z-index: 1;
}

.auth-brand {
  text-align: center;
  margin-bottom: 32px;
}

.brand-icon {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);
  transition: transform 0.3s ease;

  &:hover {
    transform: scale(1.05) rotate(3deg);
  }

  .el-icon {
    color: #fff;
  }
}

.brand-title {
  font-size: 26px;
  font-weight: 700;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
}

.brand-subtitle {
  font-size: 14px;
  color: #9CA3AF;
  margin: 0;
  font-weight: 500;
}

.auth-form {
  :deep(.el-input__wrapper) {
    border-radius: 12px;
    padding: 6px 14px;
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.15) inset;
    background: rgba(255, 255, 255, 0.8);
    transition: all 0.25s ease;

    &:hover {
      box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.3) inset;
      background: #fff;
    }

    &.is-focus {
      box-shadow: 0 0 0 1px #6366F1 inset, 0 0 0 4px rgba(99, 102, 241, 0.1);
      background: #fff;
    }
  }

  :deep(.el-input__inner) {
    font-size: 15px;
    color: #1F2937;

    &::placeholder {
      color: #9CA3AF;
    }
  }

  :deep(.el-input__icon) {
    color: #9CA3AF;
  }
}

.submit-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
  border: none;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
  transition: all 0.25s ease;
  margin-top: 8px;

  &:hover:not([disabled]) {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(99, 102, 241, 0.45);
  }

  &:active:not([disabled]) {
    transform: translateY(0);
  }
}

.auth-footer {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid rgba(99, 102, 241, 0.1);
  font-size: 14px;
  color: #9CA3AF;
}

.link {
  font-size: 13px;
  color: #6B7280;
  text-decoration: none;
  transition: all 0.25s ease;

  &:hover {
    color: #6366F1;
  }

  &-primary {
    font-weight: 600;
    color: #6366F1;

    &:hover {
      color: #4F46E5;
      text-decoration: underline;
    }
  }
}

:deep(.el-form-item__error) {
  font-size: 12px;
  color: #EF4444;
}

@media (max-width: 480px) {
  .auth-card {
    padding: 32px 24px;
    border-radius: 16px;
  }

  .brand-title {
    font-size: 22px;
  }
  
  .brand-icon {
    width: 64px;
    height: 64px;
  }
}
</style>
