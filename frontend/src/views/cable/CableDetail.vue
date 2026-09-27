<template>
  <!-- 明细面板：与列表、整段查看读取同一个结果对象 -->
  <article v-if="result" class="cable-detail card">
    <header class="detail-head">
      <div>
        <h3>{{ result.电缆编号 }}</h3>
        <p class="page-desc">{{ result.起止位置 }}</p>
      </div>
      <ConclusionBadge :result="result" />
    </header>

    <dl class="detail-grid">
      <div v-for="field in detailFields" :key="field" class="detail-item">
        <dt>{{ field }}</dt>
        <dd>{{ displayValue(result[field]) }}</dd>
      </div>
      <div class="detail-item">
        <dt>当前流转状态</dt>
        <dd>{{ result.status }}</dd>
      </div>
    </dl>

    <section class="detail-history">
      <h4>绝缘电阻测值趋势（MΩ）</h4>
      <p v-if="!result.history.length" class="empty-inline">暂无测值记录，结论按测值缺失处理</p>
      <ol v-else class="history-list">
        <li v-for="point in result.history" :key="point.date">
          <span>{{ point.date }}</span>
          <strong>{{ point.value === null ? '—' : point.value }}</strong>
        </li>
      </ol>
    </section>
  </article>
</template>

<script setup lang="ts">
import ConclusionBadge from './ConclusionBadge.vue'
import { displayValue, type CableResult } from './result'

defineProps<{ result: CableResult }>()

const detailFields = ['电缆型号', '敷设方式', '绝缘电阻', '测试日期'] as const
</script>
