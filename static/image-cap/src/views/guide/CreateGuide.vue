<template>
  <div class="guide">

  <!-- 走马灯 -->
    <div class="carousel" @mouseenter="pauseAuto" @mouseleave="startAuto">
      <div
        class="slide-wrapper"
        :class="direction"
        :key="direction + '-' + currentIndex"
      >
        <img class="current" :src="currentImage" />
        <img class="next" :src="nextImage" />
      </div>


      <button class="arrow left" @click="prev">‹</button>
      <button class="arrow right" @click="next">›</button>
    </div>


    <!-- 指示点 -->
    <div class="dots">
      <span
        v-for="(_, index) in images"
        :key="index"
        :class="{ active: index === currentIndex }"
        @click="go(index)"
      />
    </div>


    <!-- 介绍文字 -->
    <div class="intro">
      <h2>协同标注平台</h2>
      <p>
        支持多人协作标注、任务流转、进度可视化，
        帮助团队高效完成数据标注工作。
      </p>
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

const currentIndex = ref(0)
const direction = ref<'next' | 'prev'>('next')
const animating = ref(false)

const startAuto = () => {
  if (timer) clearInterval(timer)
  timer = window.setInterval(() => next(), 3000)
}
const pauseAuto = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const currentImage = computed(() => images[currentIndex.value])
const nextImage = computed(() => {
  return direction.value === 'next'
    ? images[(currentIndex.value + 1) % images.length]
    : images[(currentIndex.value - 1 + images.length) % images.length]
})

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

const run = () => {
  animating.value = true
  setTimeout(() => {
    currentIndex.value =
      direction.value === 'next'
        ? (currentIndex.value + 1) % images.length
        : (currentIndex.value - 1 + images.length) % images.length
    animating.value = false
  }, 500)
}

// ---------- 自动轮播 ----------
let timer: number

onMounted(() => {
  startAuto() // 组件挂载后启动自动轮播
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

</script>



<style scoped>
.carousel {
  position: relative;
  width: 760px;
  height: 360px;
  overflow: hidden;
}

.slide-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

/* 两张图 */
.slide-wrapper img {
  position: absolute;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 默认状态下，next 不显示在视区 */
.slide-wrapper .next {
  transform: translateX(100%);
}


/* 👉 下一张（右 → 左） */
.slide-wrapper.next .current {
  transform: translateX(0);
  animation: slide-out-left 0.5s forwards;
}

.slide-wrapper.next .next {
  transform: translateX(100%);
  animation: slide-in-left 0.5s forwards;
}

/* 👈 上一张（左 → 右） */
.slide-wrapper.prev .current {
  transform: translateX(0);
  animation: slide-out-right 0.5s forwards;
}

.slide-wrapper.prev .next {
  transform: translateX(-100%);
  animation: slide-in-right 0.5s forwards;
}

@keyframes slide-out-left {
  to { transform: translateX(-100%); }
}

@keyframes slide-in-left {
  to { transform: translateX(0); }
}

@keyframes slide-out-right {
  to { transform: translateX(100%); }
}

@keyframes slide-in-right {
  to { transform: translateX(0); }
}

.arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;

  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;

  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  font-size: 24px;
  cursor: pointer;
}

.arrow.left {
  left: 16px;
}

.arrow.right {
  right: 16px;
}



</style>

