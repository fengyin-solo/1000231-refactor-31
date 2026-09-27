<template>
  <section class="page" data-module="cable">
    <header class="page-head">
      <div>
        <h2>电缆线路管理</h2>
        <p class="page-desc">
          维护电缆段，围绕电缆编号、电缆型号、起止位置、敷设方式做登记与筛选。
          测值缺失、连续下降、待测由后端统一评估，列表、详情、异常入口读取同一份结果。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记电缆段</button>
        <button class="btn" type="button" @click="exportRows">导出电缆线路清单</button>
      </div>
    </header>

    <nav class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
        <span v-if="tab.key === 'abnormal' && abnormalCount" class="tab-badge">{{ abnormalCount }}</span>
      </button>
    </nav>

    <!-- 列表 + 逐条检查 -->
    <template v-if="activeTab === 'list'">
      <form class="filter-bar" @submit.prevent="reloadList">
        <label class="filter-item">
          <span>电缆编号</span>
          <input v-model="keyword" placeholder="按电缆编号检索" />
        </label>
        <button class="btn" type="submit">查询</button>
        <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
      </form>

      <CableTable
        :items="rows"
        show-actions
        empty-text="暂无电缆线路数据，可先登记电缆段"
        @action="onAction"
        @inspect="inspectOne"
      />

      <footer class="page-foot">
        <span>共 {{ total }} 条电缆线路记录</span>
        <button class="link" type="button" @click="checkAll">逐条检查全部电缆段</button>
        <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      </footer>
    </template>

    <!-- 异常入口 -->
    <template v-else-if="activeTab === 'abnormal'">
      <p class="page-desc">异常入口只列出评估为「测值缺失 / 连续下降」的电缆段。</p>
      <CableTable
        :items="abnormalRows"
        empty-text="当前没有评估异常的电缆段"
        @inspect="inspectOne"
      />
    </template>

    <!-- 整段查看 -->
    <template v-else-if="activeTab === 'segment'">
      <SegmentView v-if="segment" :summary="segment" @inspect="inspectOne" />
    </template>

    <!-- 详情：逐条检查与整段查看共用，展示同一份结果对象 -->
    <template v-else-if="activeTab === 'detail' && current">
      <button class="btn ghost" type="button" @click="backTo(previousTab)">返回</button>
      <CableDetail :result="current" class="detail-block" />
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  fetchCableAbnormal,
  fetchCableDetail,
  fetchCableList,
  fetchCableSegmentSummary,
  runCableAction,
} from './api'
import CableDetail from './CableDetail.vue'
import CableTable from './CableTable.vue'
import SegmentView from './SegmentView.vue'
import type { CableResult, CableSegmentSummary } from './result'

type TabKey = 'list' | 'abnormal' | 'segment' | 'detail'

const ENDPOINT = '/api/cable'
const tabs: { key: TabKey; label: string }[] = [
  { key: 'list', label: '列表' },
  { key: 'abnormal', label: '异常入口' },
  { key: 'segment', label: '整段查看' },
]

const activeTab = ref<TabKey>('list')
const previousTab = ref<TabKey>('list')

const rows = ref<CableResult[]>([])
const abnormalRows = ref<CableResult[]>([])
const segment = ref<CableSegmentSummary | null>(null)
const current = ref<CableResult | null>(null)

const total = ref(0)
const keyword = ref('')
const errorMessage = ref('')

const abnormalCount = ref(0)

async function reloadList() {
  errorMessage.value = ''
  try {
    const filters: Record<string, string> = {}
    if (keyword.value.trim()) filters.keyword = keyword.value.trim()
    const payload = await fetchCableList(filters)
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电缆线路列表读取失败'
  }
}

async function reloadAbnormal() {
  try {
    abnormalRows.value = await fetchCableAbnormal()
    abnormalCount.value = abnormalRows.value.length
  } catch {
    abnormalRows.value = []
    abnormalCount.value = 0
  }
}

async function reloadSegment() {
  try {
    segment.value = await fetchCableSegmentSummary()
  } catch {
    segment.value = null
  }
}

async function switchTab(tab: TabKey) {
  activeTab.value = tab
  if (tab === 'abnormal') await reloadAbnormal()
  if (tab === 'segment') await reloadSegment()
  if (tab === 'list') await reloadList()
}

function backTo(tab: TabKey) {
  void switchTab(tab)
}

/** 逐条检查：详情读取的就是评估后的同一份结果对象。 */
async function inspectOne(result: CableResult) {
  previousTab.value = activeTab.value === 'detail' ? 'list' : activeTab.value
  errorMessage.value = ''
  try {
    current.value = await fetchCableDetail(result.id)
    activeTab.value = 'detail'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电缆段详情读取失败'
  }
}

/** 逐条检查全部：逐条拉取的结论与整段查看使用同一套评估，结论必然一致。 */
async function checkAll() {
  errorMessage.value = ''
  try {
    segment.value = await fetchCableSegmentSummary()
    activeTab.value = 'segment'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '逐条检查失败'
  }
}

async function onAction(action: string, result: CableResult) {
  errorMessage.value = ''
  try {
    await runCableAction(result.id, action)
    await reloadList()
    await reloadAbnormal()
    await reloadSegment()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '电缆线路操作失败'
  }
}

function resetFilters() {
  keyword.value = ''
  void reloadList()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '电缆段登记入口尚未接入审批流'
}

onMounted(() => {
  void reloadList()
  void reloadAbnormal()
})
</script>

<style scoped>
.tab-bar {
  display: flex;
  gap: 8px;
  margin: 12px 0 16px;
}

.tab-item {
  position: relative;
  padding: 6px 16px;
  border: 1px solid var(--border-color, #d9d9d9);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.tab-item.active {
  border-color: #1677ff;
  color: #1677ff;
  font-weight: 600;
}

.tab-badge {
  margin-left: 6px;
  padding: 0 6px;
  border-radius: 10px;
  background: #ff4d4f;
  color: #fff;
  font-size: 12px;
}

.detail-block {
  margin-top: 12px;
}

.cable-table .row-abnormal td {
  background: #fff7f7;
}

.conclusion-badge {
  display: inline-flex;
  flex-direction: column;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 13px;
}

.conclusion-badge.is-normal {
  background: #f6ffed;
  color: #389e0d;
}

.conclusion-badge.is-pending {
  background: #fffbe6;
  color: #d48806;
}

.conclusion-badge.is-abnormal {
  background: #fff1f0;
  color: #cf1322;
}

.conclusion-hint {
  font-size: 11px;
  opacity: 0.8;
}

.is-normal-text { color: #389e0d; }
.is-pending-text { color: #d48806; }
.is-abnormal-text { color: #cf1322; }

.detail-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin: 0 0 16px;
}

.detail-item dt {
  font-size: 12px;
  color: #888;
}

.detail-item dd {
  margin: 4px 0 0;
  font-weight: 600;
}

.history-list {
  display: flex;
  gap: 16px;
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
}

.history-list li {
  display: flex;
  flex-direction: column;
  padding: 8px 12px;
  border: 1px solid #eee;
  border-radius: 6px;
}

.empty-inline {
  color: #999;
}
</style>
