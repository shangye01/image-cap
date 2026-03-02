<template>
  <div class="history-page">
    <header class="top-nav">
      <nav class="nav-list">
        <button
          v-for="item in navItems"
          :key="item"
          class="nav-item"
          :class="{ active: activeNav === item }"
          type="button"
          @click="activeNav = item"
        >
          {{ item }}
          <span v-if="item === '分享管理'" class="upgrade"></span>
        </button>
      </nav>

      <div class="header-actions">
        <button class="invite-btn" type="button">邀请成员<span class="dot"></span></button>
        <button class="add-btn" type="button">＋ 添加</button>
      </div>
    </header>

    <section class="toolbar">
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          class="tab"
          :class="{ active: activeTab === tab }"
          type="button"
          @click="activeTab = tab"
        >
          {{ tab }}
        </button>
      </div>

      <div class="filters">
        <button v-for="filter in filters" :key="filter" class="filter-btn" type="button">
          {{ filter }}
          <span class="arrow">⌄</span>
        </button>

        <button class="icon-btn" type="button" aria-label="排序">↕</button>
        <button class="icon-btn" type="button" aria-label="网格">◫</button>
      </div>
    </section>

    <main class="empty-state">
      <img class="empty-image" src="/image/uploadFolder.svg" alt="empty" />
      <h2>拖放文件到这里，开始图片标注</h2>
      <p>点击上传文件，支持上传本地文件</p>
      <div class="empty-actions">
        <button type="button" class="primary">上传文件</button>
      </div>
    </main>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'

const navItems = ['我的空间', '最近', '草稿箱', '回收站', '分享管理']
const tabs = ['全部 (0)', '作品', '我上传的']
const filters = ['颜色', '类别', '类型', '标签', '添加时间']

const activeNav = ref('回收站')
const activeTab = ref('全部 (0)')
const showChildren = ref(false)
</script>

<style scoped>
.history-page {
  background: #f5f5f7;
  padding: 20px 18px;
  color: #1f2329;
}

.top-nav,
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-list,
.tabs,
.filters,
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-item,
.tab,
.filter-btn,
.icon-btn {
  border: none;
  background: transparent;
  color: #666f7a;
  font-size: 15px;
  cursor: pointer;
}

.nav-item,
.tab {
  font-size: 16px;
  padding: 8px 0;
  margin-right: 18px;
}

.nav-item.active,
.tab.active {
  color: #222;
  border-bottom: 2px solid #222;
}

.upgrade {
  margin-left: 6px;
  font-size: 12px;
  color: #fff;
  border-radius: 8px;
  padding: 1px 6px;
}

.invite-btn,
.add-btn,
.primary {
  border: none;
  border-radius: 10px;
  height: 38px;
  padding: 0 16px;
  font-size: 16px;
  cursor: pointer;
}

.invite-btn {
  background: #fff;
  border: 1px solid #e4e6eb;
  position: relative;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  position: absolute;
  right: 12px;
  top: 8px;
}

.add-btn,
.primary {
  background: #2d5cff;
  color: #fff;
}

.toolbar {
  margin-top: 18px;
}

.tab {
  font-size: 16px;
  margin-right: 8px;
}

.filters {
  gap: 16px;
}

.filter-btn,
.switch-text,
.icon-btn {
  font-size: 16px;
  color: #2e3238;
}

.arrow {
  margin-left: 6px;
  color: #9ba0a8;
}

.switch-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.switch-input {
  display: none;
}

.switch {
  width: 36px;
  height: 20px;
  border-radius: 10px;
  background: #d7dbe2;
  position: relative;
}

.switch::after {
  content: '';
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  position: absolute;
  top: 3px;
  left: 3px;
  transition: all 0.2s ease;
}

.switch-input:checked + .switch {
  background: #2d5cff;
}

.switch-input:checked + .switch::after {
  left: 19px;
}

.empty-state {
  height: calc(100vh - 190px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.empty-image {
  width: 150px;
  margin-bottom: 22px;
}

h2 {
  margin: 0;
  font-size: 36px;
}

p {
  color: #8b93a1;
  font-size: 16px;
}

.empty-actions {
  display: flex;
  gap: 14px;
  margin-top: 14px;
}

.float-actions {
  position: fixed;
  right: 28px;
  bottom: 94px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.float-actions button {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  border: 1px solid #e5e7ec;
  background: #fff;
  cursor: pointer;
  font-size: 22px;
}
</style>