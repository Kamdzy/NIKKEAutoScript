<script setup lang="ts">
const props = defineProps<{ data: any; loading?: boolean; language?: string }>()

// Kamdzy - localize hardcoded Chinese so en-US client stops leaking source strings
const labels: Record<string, Record<string, string>> = {
  '正在读取仓库记录…': { 'en-US': 'Reading warehouse records…', 'ja-JP': '倉庫記録を読み込み中…' },
  '暂无仓库物品记录。': { 'en-US': 'No warehouse item records yet.', 'ja-JP': '倉庫アイテムの記録がありません。' },
  '物品': { 'en-US': 'Items', 'ja-JP': 'アイテム' },
  '持有': { 'en-US': 'Held', 'ja-JP': '所持' },
  '更新于': { 'en-US': 'Updated', 'ja-JP': '更新' },
}
function t(source: string) {
  const language = props.language || 'zh-CN'
  return language === 'zh-CN' ? source : labels[source]?.[language] || source
}

function count(value: any) {
  const number = Number(String(value ?? '').replace(/,/g, ''))
  return Number.isFinite(number) ? number.toLocaleString() : (value || '—')
}
</script>

<template>
  <div class="special-field warehouse-field">
    <div v-if="loading" class="special-empty">{{ t('正在读取仓库记录…') }}</div>
    <div v-else-if="!data?.groups?.length" class="special-empty">{{ t('暂无仓库物品记录。') }}</div>
    <section v-for="group in data?.groups || []" :key="group.name" class="warehouse-group">
      <header><strong>{{ group.name || t('物品') }}</strong><span>{{ group.items?.length || 0 }}</span></header>
      <div class="warehouse-grid">
        <article v-for="item in group.items || []" :key="item.id || item.name" class="warehouse-item">
          <img v-if="item.icon" :src="item.icon" :alt="item.display_name || item.name" loading="lazy">
          <span v-else class="warehouse-fallback">—</span>
          <div><div>{{ item.display_name || item.name || item.id }}</div><small>{{ t('持有') }} <b>{{ count(item.count) }}</b></small></div>
        </article>
      </div>
    </section>
    <small v-if="data?.updated_at" class="special-updated">{{ t('更新于') }} {{ data.updated_at }}</small>
  </div>
</template>
