<template>
  <!-- 结论徽章：只展示结果对象字段，判定不在这里 -->
  <span class="conclusion-badge" :class="conclusionClass(result)">
    {{ result.conclusion }}
    <small class="conclusion-hint">{{ conclusionHint(result) }}</small>
  </span>
</template>

<script setup lang="ts">
import { conclusionClass, conclusionHint, type CableResult } from './result'

defineProps<{ result: CableResult }>()
</script>
