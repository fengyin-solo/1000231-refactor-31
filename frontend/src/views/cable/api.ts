/** 电缆段数据加载：列表、详情、异常入口、整段查看都取后端那份结果对象。 */
import { fetchJson, request } from '@/api/client'

import type { CableResult, CableSegmentSummary } from './result'

const ENDPOINT = '/api/cable'

interface PagePayload {
  items: CableResult[]
  total: number
}

export function fetchCableList(filters: Record<string, string> = {}): Promise<PagePayload> {
  const query = new URLSearchParams(filters).toString()
  return fetchJson<PagePayload>(`${ENDPOINT}?${query}`)
}

export function fetchCableDetail(id: number): Promise<CableResult> {
  return fetchJson<CableResult>(`${ENDPOINT}/${id}`)
}

export async function fetchCableAbnormal(): Promise<CableResult[]> {
  const payload = await fetchJson<{ items: CableResult[] }>(`${ENDPOINT}/abnormal`)
  return payload.items
}

export function fetchCableSegmentSummary(): Promise<CableSegmentSummary> {
  return fetchJson<CableSegmentSummary>(`${ENDPOINT}/segment-summary`)
}

export async function runCableAction(id: number, action: string): Promise<void> {
  const response = await request(`${ENDPOINT}/${id}/actions`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
  if (!response.ok) {
    throw new Error('电缆线路动作未生效，请稍后重试')
  }
}
