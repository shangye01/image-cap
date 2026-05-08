<template>
  <div class="project-detail-container">
    <header class="detail-header">
      <div class="left-box">
        <button class="back-btn" @click="$router.push('/app/history')">
          <span class="icon">←</span> 返回列表
        </button>
        <div class="divider"></div>
        <div class="project-info">
          <h2 class="title">{{ currentProject?.name || '未命名文件夹' }}</h2>
          <p class="subtitle">{{ currentProject?.createTime }} · 共 {{ currentProject?.fileCount || 0 }} 张图片</p>
        </div>
      </div>
      
      <div class="right-box">
        <button class="action-btn primary" @click="startAnnotating">开始标注</button>


        <button class="action-btn">批量管理</button>
      </div>
    </header>

    <main class="image-content">
      <div class="image-grid">
        <div v-for="n in (currentProject?.fileCount || 12)" :key="n" class="image-item">
          <div class="img-wrapper">
            <img 
              :src="`https://picsum.photos/400/400?random=${n + (currentProject?.id || 0)}`" 
              loading="lazy"
            />
            <div class="overlay">
              <span class="size-tag">1280 × 720</span>
              <input type="checkbox" class="select-check" @click.stop />
            </div>
          </div>
          <p class="file-name">IMG_{{ 1000 + n }}.jpg</p>
        </div>

        <div class="image-item add-block" @click="handleAddMore">
          <div class="add-inner">
            <span class="plus">＋</span>
            <p>继续添加</p>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
const router = useRouter()
const route = useRoute()


const startAnnotating = () => {
  if (currentProject.value) {
    // 跳转到标注页面，并携带项目 ID
    router.push({
      name: 'annotate',
      params: { id: currentProject.value.id }
    });
  }
}


const currentProject = ref<any>(null)

onMounted(() => {
  // 1. 获取 URL 中的项目 ID
  const projectId = route.params.id
  
  // 2. 从本地存储获取所有数据
  const allProjects = JSON.parse(localStorage.getItem('my_projects') || '[]')
  
  // 3. 查找匹配的项目
  const found = allProjects.find((p: any) => p.id.toString() === projectId)
  
  if (found) {
    currentProject.value = found
  } else {
    console.error('项目不存在')
  }
})

const handleAddMore = () => {
  alert('触发文件夹增量上传逻辑')
}
</script>

<style scoped>
.project-detail-container {
  min-height: 100vh;
  background: #ffffff;
  padding: 0 24px 40px;
}

/* 顶部样式 */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid #f0f0f2;
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
}

.left-box {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  border: 1px solid #e5e7eb;
  background: white;
  padding: 8px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.back-btn:hover { background: #f9fafb; }

.divider {
  width: 1px;
  height: 24px;
  background: #e5e7eb;
}

.title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #8b93a1;
}

.action-btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: white;
  margin-left: 10px;
  cursor: pointer;
}

.action-btn.primary {
  background: #2d5cff;
  color: white;
  border: none;
}

/* 网格布局样式 */
.image-content {
  margin-top: 24px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 20px;
}

.image-item {
  display: flex;
  flex-direction: column;
}

.img-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  background: #f3f4f6;
  border-radius: 12px;
  overflow: hidden;
  cursor: zoom-in;
}

.img-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.image-item:hover img {
  transform: scale(1.08);
}

.overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.2);
  opacity: 0;
  transition: opacity 0.2s;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 8px;
}

.img-wrapper:hover .overlay {
  opacity: 1;
}

.size-tag {
  color: white;
  font-size: 10px;
  background: rgba(0,0,0,0.4);
  padding: 2px 6px;
  border-radius: 4px;
  align-self: flex-start;
}

.select-check {
  align-self: flex-end;
  width: 18px;
  height: 18px;
}

.file-name {
  margin-top: 8px;
  font-size: 13px;
  color: #374151;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 继续添加块 */
.add-block {
  cursor: pointer;
}

.add-inner {
  width: 100%;
  aspect-ratio: 1;
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  transition: all 0.2s;
}

.add-inner:hover {
  border-color: #2d5cff;
  color: #2d5cff;
  background: #f0f4ff;
}

.plus { font-size: 32px; margin-bottom: 4px; }
</style>