<template>
  <!-- 结果表：列表与异常入口共用，行数据全部是 CableResult -->
  <table class="data-table cable-table">
    <thead>
      <tr>
        <th v-for="column in CABLE_COLUMNS" :key="column">{{ column }}</th>
        <th>评估结论</th>
        <th v-if="showActions">可执行动作</th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="result in items"
        :key="result.id"
        :class="{ 'row-abnormal': result.abnormal }"
      >
        <td v-for="column in CABLE_COLUMNS" :key="column">{{ displayValue(result[column]) }}</td>
        <td>
          <ConclusionBadge :result="result" />
        </td>
        <td v-if="showActions" class="row-actions">
          <button
            v-for="action in actions"
            :key="action"
            class="link"
            type="button"
            @click="$emit('action', action, result)"
          >
            {{ action }}
          </button>
          <button class="link" type="button" @click="$emit('inspect', result)">查看详情</button>
        </td>
      </tr>
      <tr v-if="!items.length">
        <td :colspan="CABLE_COLUMNS.length + (showActions ? 2 : 1)" class="empty-state">
          {{ emptyText }}
        </td>
      </tr>
    </tbody>
  </table>
</template>

<script setup lang="ts">
import ConclusionBadge from './ConclusionBadge.vue'
import { CABLE_COLUMNS, displayValue, type CableResult } from './result'

defineProps<{
  items: CableResult[]
  showActions?: boolean
  emptyText?: string
}>()

defineEmits<{
  (event: 'action', action: string, result: CableResult): void
  (event: 'inspect', result: CableResult): void
}>()

const actions = ['测试绝缘', '标记隐患', '安排修复']
</script>
