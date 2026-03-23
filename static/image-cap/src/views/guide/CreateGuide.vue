<template>
  <div class="guide">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
    </div>

    <!-- 主内容区 -->
    <div class="content-wrapper">
      <!-- 标题区域 -->
      <div class="header-section">
        
        <h1 class="main-title">智能协同标注平台</h1>
        <p class="subtitle">
          融合先进的人工智能技术与流畅的协作体验，为数据科学家、算法工程师和标注团队
          <br />打造的一站式数据标注解决方案，让复杂的数据准备工作变得简单高效
        </p>
      </div>

      <!-- 走马灯 -->
      <div class="carousel-container">
        <div 
          class="carousel" 
          @mouseenter="pauseAuto" 
          @mouseleave="startAuto"
        >
          <div
            class="slide-wrapper"
            :class="direction"
            :key="direction + '-' + currentIndex"
          >
            <div class="slide-image-wrapper">
              <img class="current" :src="currentImage" alt="展示图" />
              <div class="image-overlay"></div>
            </div>
            <div class="slide-image-wrapper next-wrapper">
              <img class="next" :src="nextImage" alt="下一张" />
              <div class="image-overlay"></div>
            </div>
          </div>

          <!-- 进度条 -->
          <div class="progress-bar">
            <div 
              class="progress-fill" 
              :style="{ width: progressWidth + '%' }"
            ></div>
          </div>

          <!-- 导航按钮 -->
          <button class="arrow left" @click="prev" aria-label="上一张">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <button class="arrow right" @click="next" aria-label="下一张">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>

          <!-- 图片计数器 -->
          <div class="image-counter">
            <span class="counter-current">{{ String(currentIndex + 1).padStart(2, '0') }}</span>
            <span class="counter-separator">/</span>
            <span class="counter-total">{{ String(images.length).padStart(2, '0') }}</span>
          </div>
        </div>

        <!-- 指示点 -->
        <div class="dots">
          <button
            v-for="(_, index) in images"
            :key="index"
            :class="{ active: index === currentIndex }"
            @click="go(index)"
            :aria-label="`跳转到第 ${index + 1} 张`"
          >
            <span class="dot-inner"></span>
          </button>
        </div>
      </div>

      <!-- 介绍文字 -->
      <div class="intro">
        <div class="intro-header">
          <h2 class="intro-title">为什么选择我们？</h2>
          <p class="intro-desc">
            我们深知高质量训练数据对于 AI 模型的重要性。平台采用分布式架构设计，
            支持从个人开发者到大型企业的多样化需求，已服务超过 500+ 企业客户，
            累计处理标注任务超过 1000 万条。
          </p>
        </div>
        
        <div class="feature-grid">
          <div class="feature-item" v-for="(feature, idx) in features" :key="idx">
            <div class="feature-icon-wrapper">
              <span class="feature-icon">{{ feature.icon }}</span>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.desc }}</p>
          </div>
        </div>

        <div class="stats-section">
          <div class="stat-item" v-for="(stat, idx) in stats" :key="idx">
            <div class="stat-number">{{ stat.number }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>

      
      
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const images = [
  '/image/carousel1.jpg',
  '/image/carousel2.jpeg',
  '/image/carousel3.jpeg'
]

const features = [
  { 
    icon: '👥', 
    title: '实时多人协作', 
    desc: '支持多人同时在线标注，实时同步进度，内置评论与审核机制，团队协作零延迟' 
  },
  { 
    icon: '📊', 
    title: '智能进度追踪', 
    desc: '可视化仪表盘实时展示项目进度、标注质量统计，支持自定义报表导出' 
  },
  { 
    icon: '🤖', 
    title: 'AI 预标注引擎', 
    desc: '基于深度学习的智能预标注，自动识别目标物体，标注效率提升 300%' 
  },
  { 
    icon: '🔒', 
    title: '企业级安全', 
    desc: 'SOC2 认证，端到端加密传输，细粒度权限控制，完整操作审计日志' 
  }
]

const stats = [
  { number: '500+', label: '企业客户' },
  { number: '1000万+', label: '标注任务' },
  { number: '99.9%', label: '服务可用性' },
  { number: '50+', label: '标注类型' }
]

const currentIndex = ref(0)
const direction = ref<'next' | 'prev'>('next')
const animating = ref(false)
const progress = ref(0)
let timer = ref<number | null>(null)
let progressTimer = ref<number | null>(null)

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
  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }
  if (progressTimer.value) {
    clearInterval(progressTimer.value)
    progressTimer.value = null
  }
}

const currentImage = computed(() => images[currentIndex.value])
const nextImage = computed(() => {
  return direction.value === 'next'
    ? images[(currentIndex.value + 1) % images.length]
    : images[(currentIndex.value - 1 + images.length) % images.length]
})

const progressWidth = computed(() => Math.min(progress.value, 100))

const next = () => {
  if (animating.value) return
  direction.value = 'next'
  run()
}

const prev = () => {
  if (animating.value) return
  direction.value = 'prev'
  run()
}

const go = (index: number) => {
  if (animating.value || index === currentIndex.value) return
  
  direction.value = index > currentIndex.value ? 'next' : 'prev'
  animating.value = true
  
  const targetIndex = index
  
  setTimeout(() => {
    currentIndex.value = targetIndex
    animating.value = false
    startAuto()
  }, 500)
}

const run = () => {
  animating.value = true
  setTimeout(() => {
    currentIndex.value =
      direction.value === 'next'
        ? (currentIndex.value + 1) % images.length
        : (currentIndex.value - 1 + images.length) % images.length
    animating.value = false
    progress.value = 0
  }, 500)
}

onMounted(() => {
  startAuto()
})

onUnmounted(() => {
  if (timer.value) clearInterval(timer.value)
  if (progressTimer.value) clearInterval(progressTimer.value)
})
</script>

<style scoped>
.guide {
  min-height: 100vh;
  background: linear-gradient(135deg, #fafbfc 0%, #f0f4f8 100%);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 60px 20px;
}

/* 背景装饰 */
.bg-decoration {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: float 20s infinite ease-in-out;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  top: -200px;
  right: -200px;
  animation-delay: 0s;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  bottom: -100px;
  left: -100px;
  animation-delay: -7s;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

/* 内容包装器 */
.content-wrapper {
  position: relative;
  z-index: 1;
  max-width: 1000px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
}

/* 头部区域 */
.header-section {
  text-align: center;
  animation: fadeInUp 0.8s ease-out;
  max-width: 800px;
}

.brand-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 100px;
  margin-bottom: 20px;
}

.badge-icon {
  color: #667eea;
  font-size: 14px;
}

.badge-text {
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.main-title {
  font-size: 42px;
  font-weight: 800;
  background: linear-gradient(135deg, #1a202c 0%, #4a5568 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 16px 0;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.subtitle {
  font-size: 16px;
  color: #718096;
  margin: 0;
  font-weight: 400;
  line-height: 1.8;
  max-width: 640px;
  margin: 0 auto;
}

/* 走马灯容器 - 尺寸减小 */
.carousel-container {
  width: 100%;
  max-width: 720px;
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

.carousel {
  position: relative;
  width: 100%;
  height: 360px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.5) inset;
  background: #fff;
}

.slide-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.slide-image-wrapper {
  position: absolute;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.slide-image-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.image-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    transparent 0%,
    transparent 60%,
    rgba(0, 0, 0, 0.4) 100%
  );
}

.next-wrapper {
  transform: translateX(100%);
}

/* 动画 */
.slide-wrapper.next .current {
  animation: slide-out-left 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.slide-wrapper.next .next-wrapper {
  animation: slide-in-left 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.slide-wrapper.prev .current {
  animation: slide-out-right 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.slide-wrapper.prev .next-wrapper {
  animation: slide-in-right 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

@keyframes slide-out-left {
  to { transform: translateX(-100%); }
}

@keyframes slide-in-left {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@keyframes slide-out-right {
  to { transform: translateX(100%); }
}

@keyframes slide-in-right {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}

/* 进度条 */
.progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: rgba(255, 255, 255, 0.2);
  z-index: 5;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.1s linear;
}

/* 导航按钮 */
.arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  color: #1a202c;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.arrow svg {
  width: 18px;
  height: 18px;
}

.arrow:hover {
  background: #fff;
  transform: translateY(-50%) scale(1.1);
  box-shadow: 0 6px 30px rgba(0, 0, 0, 0.2);
}

.arrow.left {
  left: 16px;
}

.arrow.right {
  right: 16px;
}

/* 图片计数器 */
.image-counter {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 10;
  display: flex;
  align-items: baseline;
  gap: 4px;
  color: #fff;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.counter-current {
  font-size: 20px;
  font-weight: 700;
}

.counter-separator {
  font-size: 12px;
  opacity: 0.6;
}

.counter-total {
  font-size: 12px;
  opacity: 0.6;
}

/* 指示点 */
.dots {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}

.dots button {
  position: relative;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dot-inner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e0;
  transition: all 0.3s ease;
}

.dots button:hover .dot-inner {
  background: #a0aec0;
  transform: scale(1.2);
}

.dots button.active .dot-inner {
  width: 24px;
  border-radius: 4px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 介绍区域 */
.intro {
  width: 100%;
  animation: fadeInUp 0.8s ease-out 0.4s both;
}

.intro-header {
  text-align: center;
  margin-bottom: 32px;
}

.intro-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 12px 0;
}

.intro-desc {
  font-size: 15px;
  color: #718096;
  line-height: 1.8;
  max-width: 720px;
  margin: 0 auto;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 40px;
}

.feature-item {
  text-align: center;
  padding: 28px 20px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
}

.feature-item:hover {
  transform: translateY(-4px);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
}

.feature-icon-wrapper {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-icon {
  font-size: 28px;
}

.feature-item h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 10px 0;
}

.feature-item p {
  font-size: 13px;
  color: #718096;
  margin: 0;
  line-height: 1.7;
}

/* 数据统计 */
.stats-section {
  display: flex;
  justify-content: center;
  gap: 60px;
  padding: 32px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #718096;
  font-weight: 500;
}

/* CTA 区域 */
.cta-section {
  width: 100%;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 40px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
  animation: fadeInUp 0.8s ease-out 0.6s both;
}

.cta-content {
  margin-bottom: 24px;
}

.cta-content h3 {
  font-size: 22px;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 8px 0;
}

.cta-content p {
  font-size: 15px;
  color: #718096;
  margin: 0;
}

.cta-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
}

.btn-primary svg {
  width: 16px;
  height: 16px;
  transition: transform 0.3s ease;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(102, 126, 234, 0.5);
}

.btn-primary:hover svg {
  transform: translateX(4px);
}

.btn-secondary {
  padding: 14px 28px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  background: transparent;
  color: #4a5568;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  border-color: #667eea;
  color: #667eea;
  background: rgba(102, 126, 234, 0.05);
}

/* 动画 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .guide {
    padding: 40px 16px;
  }
  
  .main-title {
    font-size: 28px;
  }
  
  .subtitle {
    font-size: 14px;
  }
  
  .carousel {
    height: 240px;
    border-radius: 16px;
  }
  
  .carousel-container {
    max-width: 100%;
  }
  
  .arrow {
    width: 36px;
    height: 36px;
  }
  
  .arrow.left { left: 12px; }
  .arrow.right { right: 12px; }
  
  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  
  .feature-item {
    padding: 20px 16px;
  }
  
  .stats-section {
    flex-wrap: wrap;
    gap: 24px;
    padding: 24px;
  }
  
  .stat-item {
    flex: 1;
    min-width: 100px;
  }
  
  .cta-section {
    padding: 28px 20px;
  }
  
  .cta-buttons {
    flex-direction: column;
  }
  
  .btn-primary,
  .btn-secondary {
    width: 100%;
    justify-content: center;
  }
}
</style>