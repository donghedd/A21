<template>
  <div class="ai-voice" :class="{ 'is-recording': isRecording, 'is-playing': isPlaying }">
    <!-- 语音输入按钮 -->
    <el-tooltip
      :content="isRecording ? '点击停止录音' : '点击开始语音输入'"
      placement="top"
    >
      <el-button
        :type="isRecording ? 'danger' : 'primary'"
        :icon="isRecording ? Microphone : Microphone"
        circle
        :loading="isProcessing"
        @click="toggleRecording"
        class="voice-btn"
      >
        <template #icon>
          <el-icon :size="20">
            <Microphone v-if="!isRecording" />
            <VideoPause v-else />
          </el-icon>
        </template>
      </el-button>
    </el-tooltip>

    <!-- 录音状态指示器 -->
    <div v-if="isRecording" class="recording-indicator">
      <div class="recording-waves">
        <span v-for="i in 5" :key="i" :style="{ animationDelay: `${i * 0.1}s` }"></span>
      </div>
      <span class="recording-time">{{ formatTime(recordingTime) }}</span>
    </div>

    <!-- 转写文本显示 -->
    <div v-if="transcript && showTranscript" class="transcript-panel">
      <div class="transcript-header">
        <span>语音转写</span>
        <el-button link size="small" @click="clearTranscript">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <div class="transcript-content">{{ transcript }}</div>
      <div class="transcript-actions">
        <el-button type="primary" size="small" @click="useTranscript">
          使用此文本
        </el-button>
      </div>
    </div>

    <!-- 语音播放控制 -->
    <div v-if="audioUrl" class="audio-player">
      <audio ref="audioPlayer" :src="audioUrl" @ended="onAudioEnded" @timeupdate="onTimeUpdate"></audio>
      <el-button
        :type="isPlaying ? 'primary' : 'default'"
        :icon="isPlaying ? VideoPause : VideoPlay"
        circle
        size="small"
        @click="togglePlayback"
      />
      <el-slider
        v-model="playbackProgress"
        :max="100"
        size="small"
        class="progress-slider"
        @change="seekAudio"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Microphone, VideoPause, VideoPlay, Close } from '@element-plus/icons-vue'

const props = defineProps({
  // 是否自动开始录音
  autoStart: { type: Boolean, default: false },
  // 最大录音时长（秒）
  maxDuration: { type: Number, default: 60 },
  // 是否显示转写面板
  showTranscript: { type: Boolean, default: true },
  // 语音识别语言
  language: { type: String, default: 'zh-CN' }
})

const emit = defineEmits([
  'transcript',
  'recording-start',
  'recording-stop',
  'recording-error',
  'use-transcript'
])

// 状态
const isRecording = ref(false)
const isProcessing = ref(false)
const isPlaying = ref(false)
const recordingTime = ref(0)
const transcript = ref('')
const audioUrl = ref('')
const playbackProgress = ref(0)

// 引用
const audioPlayer = ref(null)
let mediaRecorder = null
let audioChunks = []
let recordingTimer = null
let recognition = null

// 初始化语音识别
function initSpeechRecognition() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    ElMessage.warning('您的浏览器不支持语音识别功能')
    return null
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  const recognizer = new SpeechRecognition()

  recognizer.continuous = true
  recognizer.interimResults = true
  recognizer.lang = props.language

  recognizer.onresult = (event) => {
    let finalTranscript = ''
    let interimTranscript = ''

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript
      if (event.results[i].isFinal) {
        finalTranscript += transcript
      } else {
        interimTranscript += transcript
      }
    }

    if (finalTranscript) {
      transcript.value += finalTranscript
      emit('transcript', transcript.value)
    }
  }

  recognizer.onerror = (event) => {
    console.error('语音识别错误:', event.error)
    emit('recording-error', event.error)
    if (event.error !== 'no-speech') {
      ElMessage.error('语音识别出错: ' + event.error)
    }
  }

  return recognizer
}

// 开始录音
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

    // 初始化音频录制
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
      audioUrl.value = URL.createObjectURL(audioBlob)
      stream.getTracks().forEach(track => track.stop())
    }

    mediaRecorder.start()

    // 初始化语音识别
    recognition = initSpeechRecognition()
    if (recognition) {
      recognition.start()
    }

    isRecording.value = true
    recordingTime.value = 0
    emit('recording-start')

    // 开始计时
    recordingTimer = setInterval(() => {
      recordingTime.value++
      if (recordingTime.value >= props.maxDuration) {
        stopRecording()
        ElMessage.info('已达到最大录音时长')
      }
    }, 1000)

  } catch (error) {
    console.error('录音失败:', error)
    ElMessage.error('无法访问麦克风，请检查权限设置')
    emit('recording-error', error.message)
  }
}

// 停止录音
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }

  if (recognition) {
    recognition.stop()
  }

  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }

  isRecording.value = false
  isProcessing.value = false
  emit('recording-stop', { duration: recordingTime.value, transcript: transcript.value })
}

// 切换录音状态
function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
  } else {
    transcript.value = ''
    startRecording()
  }
}

// 清除转写文本
function clearTranscript() {
  transcript.value = ''
  audioUrl.value = ''
}

// 使用转写文本
function useTranscript() {
  if (transcript.value.trim()) {
    emit('use-transcript', transcript.value.trim())
    clearTranscript()
  }
}

// 格式化时间
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 音频播放控制
function togglePlayback() {
  if (!audioPlayer.value) return

  if (isPlaying.value) {
    audioPlayer.value.pause()
    isPlaying.value = false
  } else {
    audioPlayer.value.play()
    isPlaying.value = true
  }
}

function onAudioEnded() {
  isPlaying.value = false
  playbackProgress.value = 0
}

function onTimeUpdate() {
  if (audioPlayer.value && audioPlayer.value.duration) {
    playbackProgress.value = (audioPlayer.value.currentTime / audioPlayer.value.duration) * 100
  }
}

function seekAudio(value) {
  if (audioPlayer.value && audioPlayer.value.duration) {
    const time = (value / 100) * audioPlayer.value.duration
    audioPlayer.value.currentTime = time
  }
}

// 自动开始
watch(() => props.autoStart, (val) => {
  if (val && !isRecording.value) {
    startRecording()
  }
})

// 清理
onUnmounted(() => {
  stopRecording()
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
  }
})
</script>

<style scoped lang="scss">
.ai-voice {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;

  &.is-recording {
    .voice-btn {
      animation: pulse 1.5s infinite;
    }
  }
}

.voice-btn {
  width: 48px;
  height: 48px;
  transition: all 0.3s;

  &:hover {
    transform: scale(1.05);
  }
}

.recording-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.recording-waves {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 24px;

  span {
    width: 4px;
    background: #3b82f6;
    border-radius: 2px;
    animation: wave 1s ease-in-out infinite;

    &:nth-child(1) { height: 8px; }
    &:nth-child(2) { height: 16px; }
    &:nth-child(3) { height: 24px; }
    &:nth-child(4) { height: 16px; }
    &:nth-child(5) { height: 8px; }
  }
}

.recording-time {
  font-size: 14px;
  color: #6b7280;
  font-family: monospace;
}

.transcript-panel {
  width: 100%;
  max-width: 400px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  margin-top: 8px;
}

.transcript-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 600;
  color: #374151;
}

.transcript-content {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.transcript-actions {
  display: flex;
  justify-content: flex-end;
}

.audio-player {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 300px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;

  .progress-slider {
    flex: 1;
  }
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
  }
  50% {
    box-shadow: 0 0 0 12px rgba(239, 68, 68, 0);
  }
}

@keyframes wave {
  0%, 100% {
    transform: scaleY(0.5);
  }
  50% {
    transform: scaleY(1);
  }
}
</style>
