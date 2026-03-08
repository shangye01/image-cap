<template>
  <div class="layout">
    <!-- 顶部 -->
    <header class="header">
      <div class="logo">ImageCap</div>
      <div class="user">已登录</div>
    </header>

    <!-- 主体 -->
    <div class="container">
      <!-- 左侧导航 -->
      <aside class="aside">
        <nav>
          <!-- 主要导航 -->
          <router-link to="/app/guide">首页</router-link>
          <router-link to="/app/project">创建</router-link>
          <router-link to="/app/history">列表</router-link>
          
          
          
          <!-- 独立功能路由 -->
          <router-link to="/app/annotate">标注</router-link>
          <router-link to="/app/tasks">任务</router-link>
          <router-link to="/app/training">训练</router-link>
          <router-link to="/app/profile">个人中心</router-link>
        </nav>
      </aside>

      <!-- 内容区（点击后在这里显示） -->
      <main class="main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  height: 56px;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.aside {
  width: 200px;
  background: #f8fafc;
  border-right: 1px solid #e5e7eb;
  padding: 16px;
}

.aside nav {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.aside a {
  padding: 10px 12px;
  border-radius: 6px;
  text-decoration: none;
  color: #374151;
  font-size: 14px;
}

.aside a.router-link-active {
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 500;
}

.nav-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 8px 0;
}

.main {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>