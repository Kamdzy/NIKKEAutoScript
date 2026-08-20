<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../../api/client'

// Browsers cannot return an arbitrary full filesystem path, so the local
// backend opens the host-native dialog for every desktop shell.
const props = defineProps<{ value: string; picker: any; disabled?: boolean; language?: string }>()
const emit = defineEmits<{ picked: [value: string]; error: [message: string] }>()
const picking = ref(false)

// Kamdzy - localize hardcoded Chinese so en-US client stops leaking source strings
const labels: Record<string, Record<string, string>> = {
  '文件选择失败，请直接输入路径。': { 'en-US': 'File selection failed, please enter the path directly.', 'ja-JP': 'ファイル選択に失敗しました。パスを直接入力してください。' },
  '正在选择…': { 'en-US': 'Selecting…', 'ja-JP': '選択中…' },
  '选择文件': { 'en-US': 'Select file', 'ja-JP': 'ファイルを選択' },
}
function t(source: string) {
  const language = props.language || 'zh-CN'
  return language === 'zh-CN' ? source : labels[source]?.[language] || source
}

async function pick() {
  if (props.disabled || picking.value) return
  picking.value = true
  const payload = {
    mode: props.picker?.mode === 'directory' ? 'directory' : 'file',
    title: props.picker?.title || '',
    defaultPath: props.value || '',
    accept: Array.isArray(props.picker?.accept) ? props.picker.accept : [],
  }
  try {
    const reply = await api.post('/api/system/pick-path', payload)
    if (reply.ok && reply.path) emit('picked', reply.path)
    else if (!reply.canceled) emit('error', reply.error || t('文件选择失败，请直接输入路径。'))
  } catch (exception: any) {
    emit('error', exception?.message || t('文件选择失败，请直接输入路径。'))
  } finally {
    picking.value = false
  }
}
</script>

<template>
  <button type="button" class="btn" :disabled="disabled || picking" @click="pick">{{ picking ? t('正在选择…') : (picker?.button_label || t('选择文件')) }}</button>
</template>
