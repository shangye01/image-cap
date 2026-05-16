<!-- views/TaskListView.vue -->
<template>
  <div class="task-list-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>📋 任务数据中心</h1>
      <p class="subtitle">实时监控标注任务进度与效率分析</p>
    </div>

    <!-- 顶部统计卡片 -->
    <div class="stats-row">
      <div class="stat-card total">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <span class="stat-value">{{ totalTasks }}</span>
          <span class="stat-label">总任务数</span>
        </div>
        <div class="stat-trend" :class="trends.total >= 0 ? 'up' : 'down'">
          {{ trends.total >= 0 ? '↑' : '↓' }} {{ Math.abs(trends.total) }}%
        </div>
      </div>

      <div class="stat-card pending">
        <div class="stat-icon">⏳</div>
        <div class="stat-content">
          <span class="stat-value">{{ pendingTasks }}</span>
          <span class="stat-label">待标注</span>
        </div>
        <div class="stat-progress">
          <div
            class="progress-bar"
            :style="{ width: (totalTasks ? (pendingTasks / totalTasks) * 100 : 0) + '%' }"
          ></div>
        </div>
      </div>

      <div class="stat-card annotating">
        <div class="stat-icon">✏️</div>
        <div class="stat-content">
          <span class="stat-value">{{ annotatingTasks }}</span>
          <span class="stat-label">标注中</span>
        </div>
      </div>

      <div class="stat-card completed">
        <div class="stat-icon">✅</div>
        <div class="stat-content">
          <span class="stat-value">{{ completedTasks }}</span>
          <span class="stat-label">已完成</span>
        </div>
        <div class="stat-trend" :class="trends.completed >= 0 ? 'up' : 'down'">
          {{ trends.completed >= 0 ? '↑' : '↓' }} {{ Math.abs(trends.completed) }}%
        </div>
      </div>

      <div class="stat-card efficiency">
        <div class="stat-icon">🚀</div>
        <div class="stat-content">
          <span class="stat-value">{{ efficiency }}%</span>
          <span class="stat-label">完成率</span>
        </div>
        <div class="efficiency-ring" :style="{ '--progress': efficiency + '%' }">
          <svg viewBox="0 0 36 36">
            <path
              class="circle-bg"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              class="circle"
              :stroke-dasharray="efficiency + ', 100'"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <!-- 任务趋势折线图 -->
      <div class="chart-card large">
        <div class="chart-header">
          <h3>📈 任务趋势分析</h3>
          <div class="chart-actions">
            <button
              v-for="period in TREND_PERIOD_OPTIONS"
              :key="period"
              :class="['period-btn', { active: trendPeriod === period }]"
              @click="changeTrendPeriod(period)"
            >
              {{ period === 'week' ? '本周' : period === 'month' ? '本月' : '全年' }}
            </button>
          </div>
        </div>
        <v-chart class="chart" :option="trendChartOption" autoresize />
      </div>

      <!-- 任务状态分布饼图 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>🥧 任务状态分布</h3>
        </div>
        <v-chart class="chart" :option="statusChartOption" autoresize />
      </div>

      <!-- 项目任务对比柱状图 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>📊 项目对比</h3>
        </div>
        <v-chart class="chart" :option="projectChartOption" autoresize />
      </div>

      <!-- 标注效率雷达图 -->
      <!-- <div class="chart-card">
        <div class="chart-header">
          <h3>🎯 效率指标</h3>
          <span v-if="performanceSummary" class="chart-subtitle">
            综合评分 {{ performanceSummary.scores.total }} · 等级 {{ performanceSummary.level }}
          </span>
        </div>
        <v-chart class="chart" :option="radarChartOption" autoresize />
      </div> -->

      <!-- 每日完成量热力图 -->
      <div class="chart-card large">
        <div class="chart-header">
          <h3>🔥 活跃度热力图</h3>
          <span class="chart-subtitle">最近一年任务完成情况</span>
        </div>
        <v-chart class="chart" :option="heatmapOption" autoresize />
      </div>
    </div>

    <!-- 项目任务列表 -->
    <div class="projects-section">
      <h3>📁 项目详情</h3>
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        加载中...
      </div>

      <div v-else-if="Object.keys(groupedTasks).length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <p>暂无任务数据</p>
        <button class="btn-primary" @click="loadTasks">刷新数据</button>
      </div>

      <div v-else class="projects-list">
        <div
          v-for="(tasks, project) in groupedTasks"
          :key="project"
          class="project-card"
          :class="{ expanded: expandedProjects[project] }"
        >
          <div class="project-header" @click="toggleProject(project)">
            <div class="project-info">
              <span class="project-icon">📁</span>
              <div class="project-meta">
                <h4>{{ project }}</h4>
                <span class="project-count">{{ tasks.length }} 个任务</span>
              </div>
            </div>
            <div class="project-stats">
              <div class="mini-bar">
                <div
                  v-for="status in PROJECT_STATUS_SEGMENTS"
                  :key="status"
                  class="bar-segment"
                  :class="status"
                  :style="{ width: getStatusPercent(tasks, status) + '%' }"
                  :title="`${status}: ${getStatusCount(tasks, status)}`"
                ></div>
              </div>
              <span class="toggle-icon">{{ expandedProjects[project] ? '▼' : '▶' }}</span>
            </div>
          </div>

          <transition name="expand">
            <div v-show="expandedProjects[project]" class="task-list">
              <div
                v-for="task in tasks"
                :key="task.id"
                :class="['task-item', task.status]"
                @click="openTask(task)"
              >
                <div class="task-main">
                  <span class="task-id">#{{ String(task.id).slice(-6) }}</span>
                  <span class="task-time">{{ formatTime(task.created_at) }}</span>
                </div>
                <div class="task-status">
                  <span :class="['status-badge', task.status]">
                    {{ statusText(task.status) }}
                  </span>
                  <span v-if="task.annotations_count" class="annotation-count">
                    {{ task.annotations_count }} 标注
                  </span>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart, RadarChart, HeatmapChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  VisualMapComponent,
  CalendarComponent,
  RadarComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { useUserStore } from '@/stores/user'
import { getTaskCenterOverview } from '@/api/projectStorage'
import type { PerformanceSummary } from '@/api/performance'

type TaskStatus = 'pending' | 'annotating' | 'completed' | 'reviewed'

type TaskItem = {
  id: string | number
  route_task_id: string | null
  project_name: string
  status: TaskStatus
  created_at: string
  annotations_count: number
}

type ProjectStatItem = {
  project_id: string | number
  project_name: string
  created_at: string
  is_completed: boolean
  completed_at: string | null
}

type SummaryData = {
  total_images?: number
  pending_images?: number
  labeling_images?: number
  completed_images?: number
  reviewed_images?: number
}

type HeatmapPoint = [string, number]

type TrendPeriod = 'week' | 'month' | 'year'

const TREND_PERIOD_OPTIONS: TrendPeriod[] = ['week', 'month', 'year']
const PROJECT_STATUS_SEGMENTS: TaskStatus[] = ['completed', 'annotating', 'pending']

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  RadarChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  VisualMapComponent,
  CalendarComponent,
  RadarComponent,
])

const router = useRouter()
const userStore = useUserStore()

const tasks = ref<TaskItem[]>([])
const loading = ref<boolean>(false)
const expandedProjects = ref<Record<string, boolean>>({})
const trendPeriod = ref<TrendPeriod>('week')
const summary = ref<SummaryData | null>(null)
const projectStats = ref<ProjectStatItem[]>([])
const performanceSummary = ref<PerformanceSummary | null>(null)

const DAY_MS = 24 * 60 * 60 * 1000

const normalizeStatus = (status?: string | null): TaskStatus => {
  if (status === 'labeling' || status === 'annotating') return 'annotating'
  if (status === 'done' || status === 'completed') return 'completed'
  if (status === 'reviewed') return 'reviewed'
  return 'pending'
}

const toTime = (value?: string | null): number | null => {
  if (!value) return null
  const ts = new Date(value).getTime()
  return Number.isFinite(ts) ? ts : null
}

const formatDateKey = (date: Date): string => {
  const [day = ''] = date.toISOString().split('T')
  return day
}

const calcTrendPercent = (current: number, previous: number): number => {
  if (previous <= 0) return current > 0 ? 100 : 0
  return Number((((current - previous) / previous) * 100).toFixed(1))
}

const buildPerformanceMetrics = (taskList: TaskItem[]): number[] => {
  const total = taskList.length || 1
  const reviewedCount = taskList.filter((t) => t.status === 'reviewed').length
  const completedOrReviewed = taskList.filter((t) =>
    ['completed', 'reviewed'].includes(t.status)
  ).length
  const activeDays = new Set(
    taskList.map((t) => (t.created_at || '').split('T')[0]).filter(Boolean)
  ).size
  const projectCount = new Set(taskList.map((t) => t.project_name).filter(Boolean)).size || 1
  const avgAnnotations =
    taskList.reduce((sum, t) => sum + (t.annotations_count || 0), 0) / total

  return [
    Math.min(100, Math.round((completedOrReviewed / total) * 100)),
    Math.min(100, Math.round((reviewedCount / Math.max(completedOrReviewed, 1)) * 100)),
    Math.min(100, Math.round((activeDays / 30) * 100)),
    Math.min(100, Math.round((projectCount / 8) * 100)),
    Math.min(100, Math.round(Math.min(avgAnnotations * 2, 100))),
  ]
}

const trends = computed(() => {
  const now = Date.now()

  const totalCurrent = tasks.value.filter((task) => {
    const ts = toTime(task.created_at)
    return ts !== null && ts >= now - 30 * DAY_MS
  }).length

  const totalPrevious = tasks.value.filter((task) => {
    const ts = toTime(task.created_at)
    return ts !== null && ts >= now - 60 * DAY_MS && ts < now - 30 * DAY_MS
  }).length

  const completedCurrent = tasks.value.filter((task) => {
    const ts = toTime(task.created_at)
    return ts !== null && ts >= now - 30 * DAY_MS && task.status === 'completed'
  }).length

  const completedPrevious = tasks.value.filter((task) => {
    const ts = toTime(task.created_at)
    return (
      ts !== null &&
      ts >= now - 60 * DAY_MS &&
      ts < now - 30 * DAY_MS &&
      task.status === 'completed'
    )
  }).length

  return {
    total: calcTrendPercent(totalCurrent, totalPrevious),
    completed: calcTrendPercent(completedCurrent, completedPrevious),
  }
})

const totalTasks = computed(() =>
  summary.value ? Number(summary.value.total_images || 0) : tasks.value.length
)

const pendingTasks = computed(() =>
  summary.value
    ? Number(summary.value.pending_images || 0)
    : tasks.value.filter((t) => t.status === 'pending').length
)

const annotatingTasks = computed(() =>
  summary.value
    ? Number(summary.value.labeling_images || 0)
    : tasks.value.filter((t) => t.status === 'annotating').length
)

const completedTasks = computed(() =>
  summary.value
    ? Number(summary.value.completed_images || 0)
    : tasks.value.filter((t) => t.status === 'completed').length
)

const completedOnlyTasks = computed(() => completedTasks.value)

const reviewedTasks = computed(() =>
  summary.value
    ? Number(summary.value.reviewed_images || 0)
    : tasks.value.filter((t) => t.status === 'reviewed').length
)

const efficiency = computed(() => {
  if (totalTasks.value === 0) return 0
  return Math.round((completedTasks.value / totalTasks.value) * 100)
})

const groupedTasks = computed<Record<string, TaskItem[]>>(() => {
  const groups: Record<string, TaskItem[]> = {}

  tasks.value.forEach((task) => {
    const project = task.project_name || '未分类项目'
    if (!groups[project]) groups[project] = []
    groups[project].push(task)
  })

  Object.keys(groups).forEach((project) => {
    const projectTasks = groups[project]
    if (!projectTasks) return
    projectTasks.sort((a, b) => (toTime(b.created_at) || 0) - (toTime(a.created_at) || 0))
  })

  return groups
})

const trendChartOption = computed(() => {
  const days = trendPeriod.value === 'week' ? 7 : trendPeriod.value === 'month' ? 30 : 365
  const dates: string[] = []
  const completed: number[] = []
  const created: number[] = []

  const createdByDay = new Map<string, number>()
  const completedByDay = new Map<string, number>()

  if (projectStats.value.length) {
    projectStats.value.forEach((project) => {
      const createdTs = toTime(project.created_at)
      if (createdTs) {
        const createdDayKey = formatDateKey(new Date(createdTs))
        createdByDay.set(createdDayKey, (createdByDay.get(createdDayKey) || 0) + 1)
      }

      if (project.is_completed) {
        const completedTs = toTime(project.completed_at || project.created_at)
        if (completedTs) {
          const completedDayKey = formatDateKey(new Date(completedTs))
          completedByDay.set(completedDayKey, (completedByDay.get(completedDayKey) || 0) + 1)
        }
      }
    })
  } else {
    tasks.value.forEach((task) => {
      const createdTs = toTime(task.created_at)
      if (!createdTs) return
      const dayKey = formatDateKey(new Date(createdTs))
      createdByDay.set(dayKey, (createdByDay.get(dayKey) || 0) + 1)
      if (task.status === 'completed') {
        completedByDay.set(dayKey, (completedByDay.get(dayKey) || 0) + 1)
      }
    })
  }

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date()
    date.setHours(0, 0, 0, 0)
    date.setDate(date.getDate() - i)
    const dayKey = formatDateKey(date)
    dates.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }))
    created.push(createdByDay.get(dayKey) || 0)
    completed.push(completedByDay.get(dayKey) || 0)
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['新建任务', '完成任务'],
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: '#ccc' } },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#ccc' } },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series: [
      {
        name: '新建任务',
        type: 'line',
        smooth: true,
        data: created,
        itemStyle: { color: '#1890ff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.05)' },
            ],
          },
        },
      },
      {
        name: '完成任务',
        type: 'line',
        smooth: true,
        data: completed,
        itemStyle: { color: '#52c41a' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(82, 196, 26, 0.3)' },
              { offset: 1, color: 'rgba(82, 196, 26, 0.05)' },
            ],
          },
        },
      },
    ],
  }
})

const statusChartOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)',
  },
  legend: {
    orient: 'vertical',
    right: '5%',
    top: 'center',
  },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: {
        show: false,
        position: 'center',
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 20,
          fontWeight: 'bold',
        },
      },
      labelLine: { show: false },
      data: [
        { value: pendingTasks.value, name: '待处理', itemStyle: { color: '#faad14' } },
        { value: annotatingTasks.value, name: '标注中', itemStyle: { color: '#1890ff' } },
        { value: completedOnlyTasks.value, name: '已完成', itemStyle: { color: '#52c41a' } },
        { value: reviewedTasks.value, name: '已审核', itemStyle: { color: '#722ed1' } },
      ],
    },
  ],
}))

const projectChartOption = computed(() => {
  const projects = Object.keys(groupedTasks.value).slice(0, 6)
  const data = projects.map((p) => groupedTasks.value[p]?.length ?? 0)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: projects.map((p) => (p.length > 6 ? `${p.slice(0, 6)}...` : p)),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        type: 'bar',
        data: data.map((v, i) => ({
          value: v,
          itemStyle: {
            color: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'][i % 6],
          },
        })),
        barWidth: '60%',
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
})

const radarChartOption = computed(() => {
  const now = Date.now()

  const currentTasks = tasks.value.filter((task) => {
    const ts = toTime(task.created_at)
    return ts !== null && ts >= now - 30 * DAY_MS
  })

  const previousTasks = tasks.value.filter((task) => {
    const ts = toTime(task.created_at)
    return ts !== null && ts >= now - 60 * DAY_MS && ts < now - 30 * DAY_MS
  })

  const currentPerformance = performanceSummary.value
    ? [
        Number(performanceSummary.value.scores.speed || 0),
        Number(performanceSummary.value.scores.accuracy || 0),
        Number(performanceSummary.value.scores.activity || 0),
        Number(performanceSummary.value.scores.collaboration || 0),
        Number(performanceSummary.value.scores.quality || 0),
      ]
    : buildPerformanceMetrics(currentTasks)

  const previousPerformance = buildPerformanceMetrics(previousTasks)

  return {
    tooltip: {},
    radar: {
      indicator: [
        { name: '完成速度', max: 100 },
        { name: '准确率', max: 100 },
        { name: '活跃度', max: 100 },
        { name: '协作效率', max: 100 },
        { name: '质量评分', max: 100 },
      ],
      radius: '65%',
      splitNumber: 4,
      axisName: { color: '#666' },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: currentPerformance,
            name: '当前表现',
            areaStyle: { color: 'rgba(24, 144, 255, 0.3)' },
            lineStyle: { color: '#1890ff' },
            itemStyle: { color: '#1890ff' },
          },
          {
            value: previousPerformance,
            name: '上期表现',
            areaStyle: { color: 'rgba(82, 196, 26, 0.2)' },
            lineStyle: { color: '#52c41a', type: 'dashed' },
            itemStyle: { color: '#52c41a' },
          },
        ],
      },
    ],
  }
})

const heatmapOption = computed(() => {
  const data: HeatmapPoint[] = []
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 365)

  const createdByDay = new Map<string, number>()
  tasks.value.forEach((task) => {
    const ts = toTime(task.created_at)
    if (!ts) return
    const dayKey = formatDateKey(new Date(ts))
    createdByDay.set(dayKey, (createdByDay.get(dayKey) || 0) + 1)
  })

  for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
    const dateStr = formatDateKey(d)
    data.push([dateStr, createdByDay.get(dateStr) || 0])
  }

  return {
    tooltip: {
      position: 'top',
      formatter: (p: { data: [string, number] }) => `${p.data[0]}: ${p.data[1]} 个任务`,
    },
    visualMap: {
      min: 0,
      max: 10,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
      },
    },
    calendar: {
      top: '15%',
      left: '5%',
      right: '5%',
      bottom: '15%',
      range: new Date().getFullYear().toString(),
      cellSize: ['auto', 18],
      splitLine: { show: false },
      itemStyle: {
        borderWidth: 2,
        borderColor: '#fff',
        borderRadius: 4,
      },
      dayLabel: { show: false },
      monthLabel: {
        nameMap: 'cn',
        fontSize: 12,
        color: '#666',
      },
      yearLabel: { show: false },
    },
    series: [
      {
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data,
      },
    ],
  }
})

const changeTrendPeriod = (period: TrendPeriod): void => {
  trendPeriod.value = period
}

const loadTasks = async (): Promise<void> => {
  loading.value = true
  try {
    const owner = userStore.user?.username
    if (!owner) {
      tasks.value = []
      expandedProjects.value = {}
      performanceSummary.value = null
      summary.value = null
      projectStats.value = []
      return
    }

    const overview = await getTaskCenterOverview(owner)

    summary.value = overview?.summary || null

    performanceSummary.value = overview?.performance_summary?.has_data
      ? overview.performance_summary
      : null

    projectStats.value = (overview?.project_stats || [])
      .filter((item: any) => item?.project_id)
      .map((item: any): ProjectStatItem => ({
        project_id: item.project_id,
        project_name: item.project_name || '未分类项目',
        created_at: item.created_at || new Date().toISOString(),
        is_completed: Boolean(item.is_completed),
        completed_at: item.completed_at || null,
      }))

    tasks.value = (overview?.tasks || [])
      .filter((task: any) => task?.id)
      .map((task: any): TaskItem => ({
        id: task.id,
        route_task_id: task.task_id || null,
        project_name: task.project_name || '未分类项目',
        status: normalizeStatus(task.status),
        created_at: task.created_at || new Date().toISOString(),
        annotations_count: Number(task.annotations_count || 0),
      }))

    expandedProjects.value = {}
    const firstProject = Object.keys(groupedTasks.value)[0]
    if (firstProject) {
      expandedProjects.value[firstProject] = true
    }
  } catch (e) {
    console.error('加载任务失败:', e)
    performanceSummary.value = null
  } finally {
    loading.value = false
  }
}

const toggleProject = (project: string): void => {
  expandedProjects.value[project] = !expandedProjects.value[project]
}

const openTask = (task: TaskItem): void => {
  const routeTaskId = task?.route_task_id
  if (!routeTaskId) {
    window.alert('该图像暂无可进入的标注任务')
    return
  }
  router.push(`/app/annotate?task=${encodeURIComponent(routeTaskId)}`)
}

const formatTime = (timeStr?: string | null): string => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

const statusText = (status: TaskStatus): string => {
  const map: Record<TaskStatus, string> = {
    pending: '待处理',
    annotating: '标注中',
    completed: '已完成',
    reviewed: '已审核',
  }
  return map[status] || status
}

const getStatusCount = (taskList: TaskItem[], status: TaskStatus): number => {
  return taskList.filter((t) => t.status === status).length
}

const getStatusPercent = (taskList: TaskItem[], status: TaskStatus): number => {
  if (taskList.length === 0) return 0
  return (getStatusCount(taskList, status) / taskList.length) * 100
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.task-list-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

/* 页面标题 */
.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  color: #1f1f1f;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}

/* 统计卡片行 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.stat-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
}

.stat-card.total::before {
  background: #1890ff;
}
.stat-card.pending::before {
  background: #faad14;
}
.stat-card.annotating::before {
  background: #722ed1;
}
.stat-card.completed::before {
  background: #52c41a;
}
.stat-card.efficiency::before {
  background: #13c2c2;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: #f5f5f5;
}

.stat-content {
  flex: 1;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #1f1f1f;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #666;
}

.stat-trend {
  position: absolute;
  top: 16px;
  right: 16px;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
}

.stat-trend.up {
  color: #52c41a;
  background: #f6ffed;
}

.stat-trend.down {
  color: #f5222d;
  background: #fff1f0;
}

.stat-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: #f0f0f0;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #faad14, #ffc53d);
  transition: width 0.3s;
}

/* 环形进度 */
.efficiency-ring {
  width: 50px;
  height: 50px;
}

.efficiency-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.circle-bg {
  fill: none;
  stroke: #f0f0f0;
  stroke-width: 3;
}

.circle {
  fill: none;
  stroke: #13c2c2;
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s;
}

/* 图表网格 */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.chart-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.chart-card.large {
  grid-column: span 2;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-header h3 {
  font-size: 16px;
  color: #1f1f1f;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-subtitle {
  font-size: 12px;
  color: #999;
  font-weight: normal;
}

.chart-actions {
  display: flex;
  gap: 8px;
}

.period-btn {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.period-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.period-btn.active {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

.chart {
  height: 300px;
  width: 100%;
}

/* 项目列表 */
.projects-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.projects-section h3 {
  font-size: 18px;
  color: #1f1f1f;
  margin: 0 0 20px 0;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.loading {
  text-align: center;
  padding: 60px;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f0f0f0;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.btn-primary {
  padding: 10px 24px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  margin-top: 16px;
  transition: all 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

/* 项目卡片 */
.projects-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-card {
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.3s;
}

.project-card:hover {
  border-color: #d9d9d9;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  cursor: pointer;
  background: #fafafa;
  transition: background 0.2s;
}

.project-header:hover {
  background: #f5f5f5;
}

.project-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.project-icon {
  font-size: 24px;
}

.project-meta h4 {
  margin: 0 0 4px 0;
  font-size: 15px;
  color: #1f1f1f;
}

.project-count {
  font-size: 12px;
  color: #999;
}

.project-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.mini-bar {
  width: 120px;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  display: flex;
  overflow: hidden;
}

.bar-segment {
  height: 100%;
  transition: width 0.3s;
}

.bar-segment.pending {
  background: #faad14;
}
.bar-segment.annotating {
  background: #1890ff;
}
.bar-segment.completed {
  background: #52c41a;
}

.toggle-icon {
  color: #999;
  font-size: 12px;
  transition: transform 0.3s;
}

.project-card.expanded .toggle-icon {
  transform: rotate(180deg);
}

/* 任务列表 */
.task-list {
  padding: 12px;
  background: #fff;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 8px;
}

.task-item:last-child {
  margin-bottom: 0;
}

.task-item:hover {
  background: #f5f5f5;
}

.task-item.pending {
  border-left: 3px solid #faad14;
}
.task-item.annotating {
  border-left: 3px solid #1890ff;
}
.task-item.completed {
  border-left: 3px solid #52c41a;
}
.task-item.reviewed {
  border-left: 3px solid #722ed1;
}

.task-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-id {
  font-weight: 600;
  color: #1f1f1f;
  font-size: 14px;
}

.task-time {
  font-size: 12px;
  color: #999;
}

.task-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.pending {
  background: #fff7e6;
  color: #d46b08;
}

.status-badge.annotating {
  background: #e6f7ff;
  color: #096dd9;
}

.status-badge.completed {
  background: #f6ffed;
  color: #389e0d;
}

.status-badge.reviewed {
  background: #f9f0ff;
  color: #531dab;
}

.annotation-count {
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 10px;
  border-radius: 4px;
}

/* 展开动画 */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  max-height: 500px;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }

  .chart-card.large {
    grid-column: span 1;
  }

  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
