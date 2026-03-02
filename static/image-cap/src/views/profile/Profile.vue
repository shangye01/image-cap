<template>
  <div class="profile-page">
    <!-- Tabs -->
    <div class="tabs">
      <div class="tab" :class="{ active: activeTab === 1 }" @click="activeTab = 1">个人信息</div>

      <div class="tab" :class="{ active: activeTab === 2 }" @click="activeTab = 2">
        加入的团队/企业
      </div>
    </div>

    <!-- 内容 -->
    <div v-if="activeTab === 1" class="card">
      <!-- 头像 -->
      <div class="form-item">
        <div class="label">账号头像</div>
        <div class="avatar-box">
          <img src="https://img1.ttxsapp.com/avatar/default/0.png" class="avatar" />
          <!-- <div class="camera">📷</div> -->
        </div>
      </div>

      <!-- 账号名称 -->
      <div class="form-item">
        <div class="label">账号名称</div>
        <input class="input" v-model="form.name" />
      </div>

      <!-- 账号ID -->
      <div class="form-item">
        <div class="label">账号 ID</div>
        <div class="input-copy">
          <input class="input disabled" :value="form.id" disabled />
          <button class="copy-btn" @click="copyId">复制</button>
        </div>
      </div>

      <!-- 社区昵称 -->
      <div class="form-item">
        <div class="label">社区昵称</div>
        <input class="input" v-model="form.nickname" />
      </div>

      <!-- IP -->
      <div class="form-item">
        <div class="label">IP 属地</div>
        <input class="input disabled" value="四川, 成都" disabled />
      </div>

      <!-- 描述 -->
      <div class="form-item">
        <div class="label-row">
          <span>个人描述</span>
          <span class="count">{{ form.desc.length }}/200</span>
        </div>
        <textarea class="textarea" maxlength="200" v-model="form.desc"></textarea>
      </div>
    </div>

    <!-- ============ Tab 2 ============ -->
    <div v-if="activeTab === 2" class="gda-tabs-tabpane">
      <div class="gda-table-wrapper">
        <table class="gda-table">
          <thead>
            <tr>
              <th>组织名称</th>
              <th>昵称</th>
              <th>组织类型</th>
              <th>角色</th>
              <th>超级管理员</th>
              <th>加入时间</th>
              <th>操作</th>
            </tr>
          </thead>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const activeTab = ref(1)

const form = ref({
  name: '李四',
  id: '2',
  nickname: '',
  desc: '',
})

function copyId() {
  navigator.clipboard.writeText(form.value.id)
}
</script>

<style scoped>
.profile-page {
  padding: 32px;
  min-height: 100%;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 40px;
  border-bottom: 1px solid #e5e6eb;
  margin-bottom: 24px;
}

.tab {
  padding: 12px 0;
  cursor: pointer;
  font-size: 16px;
  color: #666;
  position: relative;
}

.tab.active {
  color: #111;
  font-weight: 600;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 2px;
  background: #111;
}

/* 卡片 */
.card {
  background: #fff;
  border-radius: 8px;
  padding: 0 24px;
}

/* 表单项 */
.form-item {
  padding: 24px 0;
  border-bottom: 1px solid #f0f0f0;
}

.form-item:last-child {
  border-bottom: none;
}

.label {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.label-row {
  display: flex;
  justify-content: space-between;
  font-weight: 600;
  margin-bottom: 12px;
}

.count {
  font-weight: 400;
  color: #999;
}

/* 输入框 */
.input,
.textarea {
  width: 100%;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  padding: 12px;
  font-size: 14px;
  background: #fff;
}

.input:focus,
.textarea:focus {
  outline: none;
  border-color: #111;
}

.disabled {
  background: #f3f4f6;
  color: #999;
}

/* 头像 */
.avatar-box {
  position: relative;
  width: 80px;
  height: 80px;
}

.avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
}

.camera {
  position: absolute;
  bottom: -4px;
  right: -4px;
  background: #fff;
  border-radius: 50%;
  padding: 6px;
  font-size: 12px;
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.1);
}

/* 复制 */
.input-copy {
  display: flex;
  gap: 8px;
}

.copy-btn {
  padding: 0 16px;
  background: #111;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

/* 主页拼接 */
.input-group {
  display: flex;
}

.prefix {
  background: #f3f4f6;
  border: 1px solid #e5e6eb;
  border-right: none;
  padding: 12px;
  border-radius: 6px 0 0 6px;
  font-size: 14px;
  color: #666;
}

.no-radius {
  border-radius: 0 6px 6px 0;
  border-left: none;
}

/* ======================
   Tabs
====================== */

.tabs {
  display: flex;
  gap: 40px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 24px;
}

.tab {
  font-size: 16px;
  padding-bottom: 12px;
  color: #6b7280;
  cursor: pointer;
  position: relative;
}

.tab.active {
  color: #111827;
  font-weight: 600;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 3px;
  background: #111827;
}

/* ======================
   表格容器
====================== */

.team-table {
  background: #ffffff;
  border-radius: 16px;
  padding: 0 24px;
}

/* ======================
   表头
====================== */

.table-header {
  display: flex;
  align-items: center;
  height: 56px;
  border-bottom: 1px solid #e5e7eb;
  color: #6b7280;
  font-size: 14px;
}

/* ======================
   数据行
====================== */

.table-row {
  display: flex;
  align-items: center;
  min-height: 96px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
  color: #111827;
}

/* ======================
   列宽统一
====================== */

.col {
  padding: 0 12px;
}

.name {
  width: 260px;
  display: flex;
  align-items: center;
}
.nickname {
  width: 160px;
}
.type {
  width: 120px;
}
.role {
  width: 140px;
}
.admin {
  width: 160px;
}
.time {
  width: 180px;
}
.action {
  width: 80px;
}

/* ======================
   组织名称区域
====================== */

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #e5e7eb;
  margin-right: 16px;
}

.org-title {
  font-weight: 600;
  margin-bottom: 6px;
}

.tag {
  display: inline-block;
  background: #e0ecff;
  color: #2563eb;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
}
</style>