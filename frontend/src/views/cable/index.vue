<template>
  <section class="page" data-module="cable">
    <header class="page-head">
      <div>
        <h2>电缆线路管理</h2>
        <p class="page-desc">维护电缆段，围绕电缆编号、电缆型号、起止位置、敷设方式做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记电缆段</button>
        <button class="btn" type="button" @click="exportRows">导出电缆线路清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
      <button class="btn ghost" type="button" @click="toggleAbnormal">
        {{ abnormalOnly ? '查看全部电缆段' : '只看异常段' }}
      </button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>测值结论</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td :class="{ 'conclusion-abnormal': row.测值结论?.异常 }">
            {{ row.测值结论?.结论 ?? '—' }}
          </td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">查看</button>
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无电缆线路数据，可先登记电缆段</td>
        </tr>
      </tbody>
    </table>

    <section v-if="detail" class="detail-panel">
      <header class="detail-head">
        <h3>电缆段详情：{{ detail.电缆编号 ?? detail.id }}</h3>
        <button class="btn ghost" type="button" @click="detail = null">关闭</button>
      </header>
      <dl class="detail-grid">
        <template v-for="column in columns" :key="column">
          <dt>{{ column }}</dt>
          <dd>{{ detail[column] ?? '—' }}</dd>
        </template>
        <dt>测值结论</dt>
        <dd :class="{ 'conclusion-abnormal': detail.测值结论?.异常 }">
          {{ detail.测值结论?.结论 ?? '—' }}
        </dd>
      </dl>
    </section>

    <footer class="page-foot">
      <span>共 {{ total }} 条电缆线路记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

interface SegmentResult {
  待测: boolean
  测值缺失: boolean
  连续下降: boolean
  异常: boolean
  结论: string
}

interface Row {
  id?: number | string
  测值结论?: SegmentResult
  [key: string]: unknown
}

const ENDPOINT = '/api/cable'
const columns = ["电缆编号", "电缆型号", "起止位置", "敷设方式", "绝缘电阻", "上次测值", "测试日期", "电缆状态"]
const actions = ["测试绝缘", "标记隐患", "安排修复"]
const statuses = ["正常运行", "绝缘降低", "待修复", "已修复"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = ["电缆编号", "电缆型号", "起止位置", "绝缘电阻"]
const abnormalOnly = ref(false)
const detail = ref<Row | null>(null)

// 统计卡与表格、详情读同一份测值结论，不在页面里重复判定
const stats = computed(() => {
  const results = rows.value.map((row) => row.测值结论)
  return [
    { label: '正常电缆', value: results.filter((item) => item?.结论 === '正常').length },
    { label: '异常电缆', value: results.filter((item) => item?.异常).length },
    { label: '待测电缆', value: results.filter((item) => item?.待测).length },
  ]
})

function resetFilters() {
  filters.value = {}
  abnormalOnly.value = false
  void reload()
}

function toggleAbnormal() {
  abnormalOnly.value = !abnormalOnly.value
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '电缆段登记入口尚未接入审批流'
}

async function openDetail(row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}`)
    if (!response.ok) {
      throw new Error('电缆段详情读取失败')
    }
    detail.value = (await response.json()) as Row
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电缆段详情读取失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('电缆线路动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电缆线路操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  detail.value = null
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  const base = abnormalOnly.value ? `${ENDPOINT}/abnormal` : ENDPOINT
  try {
    const response = await request(`${base}?${query}`)
    if (!response.ok) {
      throw new Error('电缆段列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电缆线路列表读取失败'
  }
}

onMounted(reload)
</script>
