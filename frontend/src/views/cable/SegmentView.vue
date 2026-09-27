<template>
  <!-- 整段查看：对全部电缆段跑同一套评估后的汇总，逐条结果与列表/详情一致 -->
  <section class="segment-view">
    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">电缆段总数</span>
        <strong class="stat-value">{{ summary.total }}</strong>
      </article>
      <article v-for="(count, label) in summary.counts" :key="label" class="stat-card">
        <span class="stat-label">{{ label }}</span>
        <strong class="stat-value" :class="countClass(label)">{{ count }}</strong>
      </article>
    </div>
    <CableTable
      :items="summary.items"
      :show-actions="false"
      empty-text="整段内暂无电缆段"
      @inspect="$emit('inspect', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import CableTable from './CableTable.vue'
import type { CableResult, CableSegmentSummary } from './result'

defineProps<{ summary: CableSegmentSummary }>()
defineEmits<{ (event: 'inspect', result: CableResult): void }>()

function countClass(label: string): string {
  if (label === '正常') return 'is-normal-text'
  if (label === '待测') return 'is-pending-text'
  return 'is-abnormal-text'
}
</script>
