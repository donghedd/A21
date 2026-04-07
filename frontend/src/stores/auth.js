import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, register, logout, getCurrentUser } from '@/api/auth'
import { getToken, setToken, removeToken } from '@/utils/storage'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(getToken())
  
  const isAuthenticated = computed(() => !!token.value)
  
  async function loginAction(credentials) {
    try {
      const response = await login(credentials)
      if (response.success) {
        token.value = response.data.token
        user.value = response.data.user
        setToken(response.data.token)
        return { success: true }
      }
      return { success: false, message: response.message }
    } catch (error) {
      return { success: false, message: error.message }
    }
  }
  
  async function registerAction(userData) {
    try {
      const response = await register(userData)
      if (response.success) {
        return { success: true }
      }
      return { success: false, message: response.message }
    } catch (error) {
      return { success: false, message: error.message }
    }
  }
  
  async function logoutAction() {
    try {
      await logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      token.value = null
      user.value = null
      removeToken()
    }
  }
  
  async function fetchUser() {
    if (!token.value) return
    try {
      const response = await getCurrentUser()
      if (response.success) {
        user.value = response.data
      }
    } catch (error) {
      console.error('Fetch user error:', error)
      await logoutAction()
    }
  }
  
  // Initialize: fetch user if token exists
  if (token.value) {
    fetchUser()
  }
  
  return {
    user,
    token,
    isAuthenticated,
    login: loginAction,
    register: registerAction,
    logout: logoutAction,
    fetchUser
  }
})
