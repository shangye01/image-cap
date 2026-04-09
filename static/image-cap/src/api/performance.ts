import request from './request'

export interface PerformanceRecentTask {
  task_id: string
  project_id?: string | null
  file_id?: string | null
  submitted_at?: string | null
  reviewed_at?: string | null
  work_seconds: number
  submitted_annotation_count: number
  reviewed_annotation_count: number
  accuracy_score: number
  efficiency_score: number
  collaboration_score: number
  quality_score: number
  total_score: number
}

export interface PerformanceSummary {
  user_id: string
  period_days: number
  has_data: boolean
  level: string
  totals: {
    all_started_tasks: number
    all_submitted_tasks: number
    all_reviewed_tasks: number
    recent_started_tasks: number
    recent_submitted_tasks: number
    recent_reviewed_tasks: number
  }
  mvp: {
    completion_rate: number
    review_coverage: number
    avg_task_minutes: number
    avg_annotations_per_task: number
  }
  scores: {
    speed: number
    accuracy: number
    activity: number
    collaboration: number
    quality: number
    stability: number
    completion: number
    total: number
  }
  trends: {
    total_delta: number
    accuracy_delta: number
    efficiency_delta: number
  }
  recent_tasks: PerformanceRecentTask[]
}

export const getMyPerformanceSummary = () =>
  request.get<{ summary: PerformanceSummary }>('/performance/me/summary')
