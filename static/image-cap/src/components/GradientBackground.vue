<template>
  <div class="bg-decoration">
    <div class="gradient-orb orb-1"></div>
    <div class="gradient-orb orb-2"></div>
    <div class="gradient-orb orb-3"></div>
  </div>
</template>

<script setup lang="ts">
// 这个组件不需要任何逻辑，纯展示
</script>

<style scoped>
.bg-decoration {
  position: fixed;  /* 固定定位，不随滚动移动 */
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;  /* 让鼠标事件穿透，不干扰点击 */
  overflow: hidden;
  z-index: 0;  /* 确保在最底层 */
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: float 20s infinite ease-in-out;
}

/* 紫色球体 */
.orb-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  top: -200px;
  right: -200px;
  animation-delay: 0s;
}

/* 粉红色球体 */
.orb-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  bottom: -100px;
  left: -100px;
  animation-delay: -7s;
}



@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}
</style>