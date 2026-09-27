/**
 * 电缆段共用结果对象：唯一数据来源。
 *
 * 判定（测值缺失 / 连续下降 / 待测）只在后端 assess_entry 一处完成，
 * 前端各入口只读取这些字段做展示，不再各自复刻判断逻辑。
 */
export type CableConclusion = '正常' | '测值缺失' | '连续下降' | '待测'

export interface CableReading {
  date: string
  value: number | null
}

export interface CableResult {
  id: number
  status: string
  /** 绝缘电阻（本期测值）缺失 */
  missing: boolean
  /** 最近连续多期测值逐期下降 */
  declining: boolean
  /** 无测试日期或距上次测试超过阈值 */
  pendingTest: boolean
  /** 评估是否异常：缺测或连续下降 */
  abnormal: boolean
  /** 评估结论，按 缺测 → 连续下降 → 待测 → 正常 取一条 */
  conclusion: CableConclusion
  history: CableReading[]
  latestValue: number | null
  电缆编号: string
  电缆型号: string
  起止位置: string
  敷设方式: string | null
  绝缘电阻: string | number | null
  测试日期: string | null
}

export interface CableSegmentSummary {
  module: string
  total: number
  abnormal: number
  counts: Record<CableConclusion, number>
  items: CableResult[]
}

/** 列表与详情共用的列，字段都来自同一份结果对象。 */
export const CABLE_COLUMNS = [
  '电缆编号',
  '电缆型号',
  '起止位置',
  '敷设方式',
  '绝缘电阻',
  '测试日期',
] as const

/** 结论对应样式标记，仅用于着色，不参与判定。 */
export function conclusionClass(result: CableResult): string {
  if (result.abnormal) return 'is-abnormal'
  if (result.pendingTest) return 'is-pending'
  return 'is-normal'
}

/** 结论旁的一句话说明，文案集中在这里维护。 */
export function conclusionHint(result: CableResult): string {
  if (result.missing) return '本期绝缘电阻测值缺失，需补测'
  if (result.declining) return '最近多期绝缘电阻连续下降，需排查'
  if (result.pendingTest) return '超过周期未测试，列入待测'
  return '测值正常'
}

/** 缺测值统一占位，保证各入口展示一致。 */
export function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || String(value).trim() === '') return '—'
  return String(value)
}
