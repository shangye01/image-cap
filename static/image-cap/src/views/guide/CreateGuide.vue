<template>
  <div class="guide">
    <GradientBackground />
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
      <div class="grid-pattern"></div>
    </div>

    <!-- 左侧信息栏 -->
    <div class="left-panel">
      <div class="brand-section">
        
        <h1 class="main-title">
          <span class="title-line">智能协同</span>
          <span class="title-line highlight">标注平台</span>
        </h1>
        <p class="subtitle">
          融合先进 AI 技术与流畅协作体验，为数据科学家与标注团队打造的一站式智能数据标注解决方案
        </p>
      </div>

      <!-- 核心指标 -->
      <div class="metrics-row">
        <div class="metric-item" v-for="(stat, idx) in stats" :key="idx">
          <div class="metric-value">{{ stat.number }}</div>
          <div class="metric-label">{{ stat.label }}</div>
          <div class="metric-trend" v-if="stat.trend">
            <span class="trend-up">↗</span> {{ stat.trend }}
          </div>
        </div>
      </div>

      <!-- 功能特性 -->
      <div class="features-list">
        <div class="feature-card" v-for="(feature, idx) in features" :key="idx" :class="{ active: activeFeature === idx }" @mouseenter="activeFeature = idx">
          <div class="feature-icon-wrapper">
            <span class="feature-icon">{{ feature.icon }}</span>
          </div>
          <div class="feature-content">
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.desc }}</p>
          </div>
          <div class="feature-arrow">→</div>
        </div>
      </div>

     

     </div>

    <!-- 右侧展示区域 -->
    <div class="right-panel">
      <!-- 主视觉卡片 -->
      <div class="showcase-card">
        <div class="card-header">
          <div class="window-controls">
            <span></span><span></span><span></span>
          </div>
          <div class="card-tabs">
            <span class="tab active">实时预览</span>
            <span class="tab">数据面板</span>
          </div>
        </div>

        <div class="card-body">
          <!-- 走马灯 -->
          <div class="carousel-wrapper" @mouseenter="pauseAuto" @mouseleave="startAuto">
            <div class="carousel-slide" :key="currentIndex">
              <img :src="images[currentIndex]" alt="展示" />
              <div class="slide-caption" v-if="currentCaption">
                <span class="caption-tag">{{ currentCaption.tag }}</span>
                <h4>{{ currentCaption.title }}</h4>
              </div>
            </div>

            <!-- 进度指示 -->
            <div class="slide-progress">
              <div v-for="(_, idx) in images" :key="idx" 
                   class="progress-segment" 
                   :class="{ active: idx === currentIndex, completed: idx < currentIndex }">
                <div class="progress-fill" v-if="idx === currentIndex" :style="{ width: progressWidth + '%' }"></div>
              </div>
            </div>

            <!-- 导航 -->
            <button class="slide-nav prev" @click="prev">‹</button>
            <button class="slide-nav next" @click="next">›</button>
          </div>

          <!-- 数据浮动卡片 -->
          <div class="floating-stats">
            <div class="float-card accuracy">
              <div class="float-icon">🎯</div>
              <div class="float-data">
                <span class="float-value">高精度</span>
                <span class="float-label">智能标注</span>
              </div>
            </div>
            <div class="float-card speed">
              <div class="float-icon">⚡</div>
              <div class="float-data">
                <span class="float-value">高效率</span>
                <span class="float-label">极速处理</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部信息条 -->
      <div class="info-bar">
        <div class="info-item">
          <span class="info-dot green"></span>
          <span>系统运行正常</span>
        </div>
        <div class="info-divider"></div>
        <div class="info-item">
          <span class="live-indicator"></span>
          <span>多团队在线协作</span>
        </div>
        <div class="info-divider"></div>
        <div class="info-item version">
          <span>稳定版本 v2.4.0</span>
        </div>
      </div>
      </div>
    </div>
    
 

  
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import GradientBackground from '@/components/GradientBackground.vue'

const images = [
  '/image/carousel1.jpg',
  '/image/carousel2.jpeg',
  '/image/carousel3.jpeg'
]

const captions = [
  { tag: '智能检测', title: 'AI 引擎自动识别标注目标' },
  { tag: '团队协作', title: '多人实时同步协作标注' },
  { tag: '质量管控', title: '全流程质量监控与审核' }
]

const features = [
  { icon: '👥', title: '实时多人协作', desc: '支持多人同时在线，实时同步，内置评论审核' },
  { icon: '🤖', title: 'AI 预标注引擎', desc: '深度学习智能识别，显著提升标注效率' },
  { icon: '📊', title: '智能进度追踪', desc: '可视化仪表盘，自定义报表导出' },
  { icon: '🔒', title: '企业级安全', desc: 'SOC2 认证，端到端加密，细粒度权限' }
]

const stats = [
  { number: '众多', label: '企业客户', trend: '持续增长中' },
  { number: '海量', label: '标注任务', trend: '高效处理中' },
  { number: '高可用', label: '服务稳定性', trend: 'SLA 保障' }
]

const showPendingReview = ref(false)
const pendingItems = ref([
  { id: 1, name: 'image_001.jpg', previewUrl: '/image/carousel1.jpg', annotationCount: 12 },
  { id: 2, name: 'image_002.jpg', previewUrl: '/image/carousel2.jpeg', annotationCount: 8 },
  { id: 3, name: 'image_003.jpg', previewUrl: '/image/carousel3.jpeg', annotationCount: 0 },
  { id: 4, name: 'image_004.jpg', previewUrl: null, annotationCount: 5 },
  { id: 5, name: 'image_005.jpg', previewUrl: '/image/carousel1.jpg', annotationCount: 20 },
  { id: 6, name: 'image_006.jpg', previewUrl: '/image/carousel2.jpeg', annotationCount: 3 }
])

const currentIndex = ref(0)
const activeFeature = ref(0)
const progress = ref(0)
const timer = ref<number | null>(null)
const progressTimer = ref<number | null>(null)

const currentCaption = computed(() => {
  if (currentIndex.value >= 0 && currentIndex.value < captions.length) {
    return captions[currentIndex.value]
  }
  return null
})

const progressWidth = computed(() => Math.min(progress.value, 100))

const startAuto = () => {
  if (timer.value) clearInterval(timer.value)
  if (progressTimer.value) clearInterval(progressTimer.value)
  progress.value = 0
  progressTimer.value = window.setInterval(() => {
    progress.value += 100 / 300
  }, 100)
  timer.value = window.setInterval(() => next(), 3000)
}

const pauseAuto = () => {
  if (timer.value) { clearInterval(timer.value); timer.value = null }
  if (progressTimer.value) { clearInterval(progressTimer.value); progressTimer.value = null }
}

const next = () => {
  currentIndex.value = (currentIndex.value + 1) % images.length
  progress.value = 0
}

const prev = () => {
  currentIndex.value = (currentIndex.value - 1 + images.length) % images.length
  progress.value = 0
}

const handleSelectItem = (item: any) => {
  console.log('选中待审核项:', item)
  showPendingReview.value = false
}

onMounted(() => startAuto())
onUnmounted(() => {
  if (timer.value) clearInterval(timer.value)
  if (progressTimer.value) clearInterval(progressTimer.value)
})
</script>

<style scoped>
.guide {
  height: 100%;
  width: 100%;
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f0fa 50%, #f5f9ff 100%);
  position: relative;
  overflow: hidden;
  display: flex;
  color: #334155;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
  min-height: 0;
  position: relative;
  z-index: 1;  /* 确保内容在背景装饰之上 */
  padding: 40px 20px;
}

/* 动态背景 */
.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  
  z-index: 1;  /* 确保内容在背景装饰之上 */
  padding: 40px 20px;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.25;
  animation: float 20s infinite ease-in-out;
}

.orb-1 {
  width: 400px; height: 400px;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  top: -100px; right: -50px;
  animation-delay: 0s;
}

.orb-2 {
  width: 350px; height: 350px;
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
  bottom: -100px; left: -100px;
  animation-delay: -7s;
}

.orb-3 {
  width: 300px; height: 300px;
  background: linear-gradient(135deg, #22d3ee 0%, #818cf8 100%);
  top: 40%; left: 60%;
  animation-delay: -14s;
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(59, 130, 246, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.04) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

/* 左侧面板 - 内容填充优化 */
.left-panel {
  flex: 0 0 46%;
  padding: 3vh 3vw;
  display: flex;
  flex-direction: column;
  justify-content: space-between; /* 改为 space-between 让内容均匀分布 */
  position: relative;
  z-index: 1;
  box-sizing: border-box;
  overflow: hidden;
  gap: 2.2vh; /* 增大间距 */
  min-height: 0;
}

.brand-section {
  flex-shrink: 0;
  padding-bottom: 0.5vh;
}

.brand-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 100px;
  margin-bottom: 1.2vh;
  backdrop-filter: blur(10px);
}

.badge-icon {
  color: #3b82f6;
  font-size: 11px;
}

.badge-text {
  font-size: 10px;
  font-weight: 700;
  color: #3b82f6;
  letter-spacing: 1.5px;
}

.main-title {
  margin: 0 0 1.5vh 0;
  line-height: 1.15;
}

.title-line {
  display: block;
  font-size: clamp(26px, 3.2vw, 40px);
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -1px;
}

.title-line.highlight {
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  font-size: clamp(12px, 0.9vw, 15px);
  color: #64748b;
  line-height: 1.7;
  margin: 0;
  max-width: 92%;
}

/* 核心指标 */
.metrics-row {
  display: flex;
  gap: 1vw;
  flex-shrink: 0;
}

.metric-item {
  flex: 1;
  padding: 1.8vh 1vw;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.metric-item:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.1);
}

.metric-value {
  font-size: clamp(16px, 1.8vw, 22px);
  font-weight: 800;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 5px;
}

.metric-label {
  font-size: 12px;
  color: #475569;
  font-weight: 500;
  margin-bottom: 5px;
}

.metric-trend {
  font-size: 10px;
  color: #10b981;
  font-weight: 600;
}

.trend-up {
  color: #10b981;
}

/* 功能列表 */
.features-list {
  display: flex;
  flex-direction: column;
  gap: 1.2vh;
  flex-shrink: 0;
}

.feature-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 1.6vh 1.2vw;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.feature-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #3b82f6 0%, #6366f1 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.feature-card:hover,
.feature-card.active {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(59, 130, 246, 0.2);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.08);
}

.feature-card.active::before {
  opacity: 1;
}

.feature-icon-wrapper {
  width: 40px;
  height: 40px;
  min-width: 40px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(99, 102, 241, 0.1) 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-icon {
  font-size: 20px;
}

.feature-content {
  flex: 1;
  min-width: 0;
}

.feature-content h3 {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 4px 0;
}

.feature-content p {
  font-size: 11px;
  color: #475569;
  margin: 0;
  line-height: 1.5;
}

.feature-arrow {
  color: #94a3b8;
  font-size: 16px;
  opacity: 0;
  transform: translateX(-10px);
  transition: all 0.3s ease;
}

.feature-card:hover .feature-arrow,
.feature-card.active .feature-arrow {
  opacity: 1;
  transform: translateX(0);
  color: #3b82f6;
}

/* CTA 区域 */
.cta-area {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
  padding: 0.5vh 0;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 1.4vh 1.8vw;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
  transition: all 0.3s ease;
}

.btn-primary svg {
  width: 16px;
  height: 16px;
  transition: transform 0.3s ease;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.4);
}

.btn-primary:hover svg {
  transform: translateX(4px);
}

.btn-ghost {
  padding: 1.4vh 1.8vw;
  border: 1.5px solid rgba(148, 163, 184, 0.3);
  border-radius: 12px;
  background: transparent;
  color: #475569;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-ghost:hover {
  border-color: rgba(59, 130, 246, 0.5);
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.05);
}

/* 信任标识 */
.trust-badges {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  padding-top: 0.5vh;
}

.trust-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.trust-icons {
  display: flex;
  gap: 8px;
}

.trust-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.2);
}

/* 右侧面板 - 严格限制 */
.right-panel {
  flex: 0 0 54%;
  padding: 3vh 3vw 3vh 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  z-index: 1;
  box-sizing: border-box;
  overflow: hidden;
  gap: 2vh;
  min-height: 0;
}

.showcase-card {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 16px;
  overflow: hidden;
  backdrop-filter: blur(20px);
  box-shadow: 
    0 25px 80px rgba(59, 130, 246, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.8) inset;
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  background: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.window-controls {
  display: flex;
  gap: 6px;
}

.window-controls span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.3);
}

.window-controls span:nth-child(1) { background: #f87171; }
.window-controls span:nth-child(2) { background: #fbbf24; }
.window-controls span:nth-child(3) { background: #34d399; }

.card-tabs {
  display: flex;
  gap: 3px;
  background: rgba(241, 245, 249, 0.8);
  padding: 3px;
  border-radius: 6px;
}

.tab {
  padding: 5px 12px;
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab.active {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.card-body {
  flex: 1;
  position: relative;
  padding: 14px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 走马灯 */
.carousel-wrapper {
  flex: 1;
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(241, 245, 249, 0.8);
  min-height: 0;
}

.carousel-slide {
  position: relative;
  width: 100%;
  height: 100%;
  animation: slideIn 0.5s ease;
}

@keyframes slideIn {
  from { opacity: 0; transform: scale(1.05); }
  to { opacity: 1; transform: scale(1); }
}

.carousel-slide img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.slide-caption {
  position: absolute;
  bottom: 14px;
  left: 14px;
  right: 14px;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.caption-tag {
  display: inline-block;
  padding: 3px 10px;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  border-radius: 100px;
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 4px;
}

.slide-caption h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.4;
}

/* 进度条 */
.slide-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  gap: 3px;
  padding: 0 14px 12px;
}

.progress-segment {
  flex: 1;
  height: 3px;
  background: rgba(148, 163, 184, 0.2);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.progress-segment.completed {
  background: linear-gradient(90deg, #3b82f6 0%, #6366f1 100%);
}

.progress-segment.active {
  background: rgba(148, 163, 184, 0.3);
}

.progress-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: linear-gradient(90deg, #3b82f6 0%, #6366f1 100%);
  transition: width 0.1s linear;
}

/* 导航按钮 */
.slide-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  color: #475569;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.3s ease;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.carousel-wrapper:hover .slide-nav {
  opacity: 1;
}

.slide-nav:hover {
  background: rgba(59, 130, 246, 0.9);
  color: #fff;
}

.slide-nav.prev { left: 12px; }
.slide-nav.next { right: 12px; }

/* 浮动统计卡片 */
.floating-stats {
  position: absolute;
  top: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 5;
}

.float-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  animation: floatCard 3s ease-in-out infinite;
}

.float-card.speed {
  animation-delay: -1.5s;
}

@keyframes floatCard {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

.float-icon {
  font-size: 20px;
}

.float-data {
  display: flex;
  flex-direction: column;
}

.float-value {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.float-label {
  font-size: 10px;
  color: #64748b;
}

/* 底部信息条 */
.info-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #475569;
  font-weight: 500;
}

.info-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.4);
}

.live-indicator {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #f87171;
  position: relative;
}

.live-indicator::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 2px solid #f87171;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(2); opacity: 0; }
}

.info-divider {
  width: 1px;
  height: 14px;
  background: rgba(148, 163, 184, 0.3);
}

.info-item.version {
  font-family: 'Courier New', monospace;
  color: #94a3b8;
}

/* 响应式 */
@media (max-width: 1200px) {
  .guide {
    flex-direction: column;
    overflow-y: auto;
    height: auto;
    min-height: 100vh;
  }

  .left-panel,
  .right-panel {
    flex: 1 1 auto;
    padding: 24px;
    width: 100%;
  }

  .title-line {
    font-size: 32px;
  }

  .metrics-row {
    gap: 12px;
  }

  .showcase-card {
    min-height: 400px;
  }
}

@media (max-width: 768px) {
  .left-panel,
  .right-panel {
    padding: 16px;
  }

  .title-line {
    font-size: 24px;
  }

  .metrics-row {
    flex-wrap: wrap;
  }

  .metric-item {
    flex: 1 1 calc(50% - 12px);
  }

  .cta-area {
    flex-direction: column;
  }

  .btn-primary,
  .btn-ghost {
    width: 100%;
    justify-content: center;
  }

  .floating-stats {
    display: none;
  }
}

/* 关键：内容层必须在背景之上 */
.content-wrapper {
  position: relative;
  z-index: 1;  /* 确保内容在背景装饰之上 */
  padding: 40px 20px;
}
</style>