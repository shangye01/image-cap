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
          <div class="progress-bar" :style="{ width: (pendingTasks / totalTasks * 100) + '%' }"></div>
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
            <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <path class="circle" :stroke-dasharray="efficiency + ', 100'" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
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
              v-for="period in ['week', 'month', 'year']" 
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
      <div class="chart-card">
        <div class="chart-header">
          <h3>🎯 效率指标</h3>
        </div>
        <v-chart class="chart" :option="radarChartOption" autoresize />
      </div>

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
                  v-for="status in ['completed', 'annotating', 'pending']" 
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
                @click="openTask(task.id)"
              >
                <div class="task-main">
                  <span class="task-id">#{{ task.id.slice(-6) }}</span>
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

<script setup>
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
  RadarComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

// 注册 ECharts 组件
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
  RadarComponent
])

const router = useRouter()
const API_BASE = 'http://localhost:8000/api'

// 数据状态
const tasks = ref([])
const loading = ref(false)
const expandedProjects = ref({})
const trendPeriod = ref('week')

// 模拟趋势数据（实际应从API获取）
const trends = ref({
  total: 12.5,
  completed: 8.3
})

// 计算属性
const totalTasks = computed(() => tasks.value.length)
const pendingTasks = computed(() => tasks.value.filter(t => t.status === 'pending').length)
const annotatingTasks = computed(() => tasks.value.filter(t => t.status === 'annotating').length)
const completedTasks = computed(() => tasks.value.filter(t => t.status === 'completed').length)
const efficiency = computed(() => {
  if (totalTasks.value === 0) return 0
  return Math.round((completedTasks.value / totalTasks.value) * 100)
})

const groupedTasks = computed(() => {
  const groups = {}
  tasks.value.forEach(task => {
    const project = task.project_name || '未分类项目'
    if (!groups[project]) groups[project] = []
    groups[project].push(task)
  })
  Object.keys(groups).forEach(project => {
    groups[project].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  })
  return groups
})

// 图表配置
const trendChartOption = computed(() => {
  const days = trendPeriod.value === 'week' ? 7 : trendPeriod.value === 'month' ? 30 : 365
  const dates = []
  const completed = []
  const created = []
  
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    dates.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }))
    completed.push(Math.floor(Math.random() * 10) + 5)
    created.push(Math.floor(Math.random() * 15) + 8)
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['新建任务', '完成任务'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: '#ccc' } }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#ccc' } },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
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
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.05)' }
            ]
          }
        }
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
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(82, 196, 26, 0.3)' },
              { offset: 1, color: 'rgba(82, 196, 26, 0.05)' }
            ]
          }
        }
      }
    ]
  }
})

const statusChartOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)'
  },
  legend: {
    orient: 'vertical',
    right: '5%',
    top: 'center'
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
        borderWidth: 2
      },
      label: {
        show: false,
        position: 'center'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 20,
          fontWeight: 'bold'
        }
      },
      labelLine: { show: false },
      data: [
        { value: pendingTasks.value, name: '待处理', itemStyle: { color: '#faad14' } },
        { value: annotatingTasks.value, name: '标注中', itemStyle: { color: '#1890ff' } },
        { value: completedTasks.value, name: '已完成', itemStyle: { color: '#52c41a' } },
        { value: tasks.value.filter(t => t.status === 'reviewed').length, name: '已审核', itemStyle: { color: '#722ed1' } }
      ]
    }
  ]
}))

const projectChartOption = computed(() => {
  const projects = Object.keys(groupedTasks.value).slice(0, 6)
  const data = projects.map(p => groupedTasks.value[p].length)
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: projects.map(p => p.length > 6 ? p.slice(0, 6) + '...' : p),
      axisLabel: { rotate: 30 }
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        type: 'bar',
        data: data.map((v, i) => ({
          value: v,
          itemStyle: {
            color: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'][i % 6]
          }
        })),
        barWidth: '60%',
        itemStyle: { borderRadius: [4, 4, 0, 0] }
      }
    ]
  }
})

const radarChartOption = computed(() => ({
  tooltip: {},
  radar: {
    indicator: [
      { name: '完成速度', max: 100 },
      { name: '准确率', max: 100 },
      { name: '活跃度', max: 100 },
      { name: '协作效率', max: 100 },
      { name: '质量评分', max: 100 }
    ],
    radius: '65%',
    splitNumber: 4,
    axisName: {
      color: '#666'
    }
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: [85, 90, 78, 88, 92],
          name: '当前表现',
          areaStyle: {
            color: 'rgba(24, 144, 255, 0.3)'
          },
          lineStyle: {
            color: '#1890ff'
          },
          itemStyle: {
            color: '#1890ff'
          }
        },
        {
          value: [70, 85, 80, 75, 80],
          name: '团队平均',
          areaStyle: {
            color: 'rgba(82, 196, 26, 0.2)'
          },
          lineStyle: {
            color: '#52c41a',
            type: 'dashed'
          },
          itemStyle: {
            color: '#52c41a'
          }
        }
      ]
    }
  ]
}))

const heatmapOption = computed(() => {
  // 生成模拟的每日数据
  const data = []
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 365)
  
  for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split('T')[0]
    const value = Math.floor(Math.random() * 10)
    data.push([dateStr, value])
  }

  return {
    tooltip: {
      position: 'top',
      formatter: (p) => `${p.data[0]}: ${p.data[1]} 个任务`
    },
    visualMap: {
      min: 0,
      max: 10,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127']
      }
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
        borderRadius: 4
      },
      dayLabel: { show: false },
      monthLabel: {
        nameMap: 'cn',
        fontSize: 12,
        color: '#666'
      },
      yearLabel: { show: false }
    },
    series: [
      {
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: data
      }
    ]
  }
})

// 方法
const changeTrendPeriod = (period) => {
  trendPeriod.value = period
}

const loadTasks = async () => {
  loading.value = true
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 800))
    
    // 生成模拟数据
    const mockTasks = []
    const projects = ['交通监控项目', '人脸识别数据集', '医学影像标注', '自动驾驶场景', '工业质检']
    const statuses = ['pending', 'annotating', 'completed', 'reviewed']
    
    for (let i = 1; i <= 45; i++) {
      mockTasks.push({
        id: `TASK-${2024}-${String(i).padStart(4, '0')}`,
        project_name: projects[Math.floor(Math.random() * projects.length)],
        status: statuses[Math.floor(Math.random() * statuses.length)],
        created_at: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
        annotations_count: Math.floor(Math.random() * 50),
        priority: ['high', 'medium', 'low'][Math.floor(Math.random() * 3)]
      })
    }
    
    tasks.value = mockTasks
    
    // 默认展开第一个项目
    const firstProject = Object.keys(groupedTasks.value)[0]
    if (firstProject) {
      expandedProjects.value[firstProject] = true
    }
  } catch (e) {
    console.error('加载任务失败:', e)
  } finally {
    loading.value = false
  }
}

const toggleProject = (project) => {
  expandedProjects.value[project] = !expandedProjects.value[project]
}

const openTask = (taskId) => {
  router.push(`/annotate?task=${taskId}`)
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

const statusText = (status) => {
  const map = {
    'pending': '待处理',
    'annotating': '标注中',
    'completed': '已完成',
    'reviewed': '已审核'
  }
  return map[status] || status
}

const getStatusCount = (tasks, status) => {
  return tasks.filter(t => t.status === status).length
}

const getStatusPercent = (tasks, status) => {
  if (tasks.length === 0) return 0
  return (getStatusCount(tasks, status) / tasks.length) * 100
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

.stat-card.total::before { background: #1890ff; }
.stat-card.pending::before { background: #faad14; }
.stat-card.annotating::before { background: #722ed1; }
.stat-card.completed::before { background: #52c41a; }
.stat-card.efficiency::before { background: #13c2c2; }

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
  to { transform: rotate(360deg); }
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

.bar-segment.pending { background: #faad14; }
.bar-segment.annotating { background: #1890ff; }
.bar-segment.completed { background: #52c41a; }

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

.task-item.pending { border-left: 3px solid #faad14; }
.task-item.annotating { border-left: 3px solid #1890ff; }
.task-item.completed { border-left: 3px solid #52c41a; }
.task-item.reviewed { border-left: 3px solid #722ed1; }

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