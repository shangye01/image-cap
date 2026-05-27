<template>
  <teleport to="body">
    <transition name="preview-fade">
      <div v-if="visible" class="pending-review-mask" @click="emit('close')">
        <div class="pending-review-panel" @click.stop>
          <div class="pending-review-header">
            <div class="pending-review-title">待审核内容</div>
            <button type="button" class="pending-review-close" @click="emit('close')">×</button>
          </div>

          <div class="pending-review-body">
            <div v-if="items.length" class="pending-review-grid">
              <button
                v-for="item in items"
                :key="item.id"
                type="button"
                class="pending-review-item"
                @click="emit('select', item)"
              >
                <img
                  v-if="item.previewUrl"
                  :src="item.previewUrl"
                  :alt="item.name"
                  class="pending-review-thumb"
                />
                <div v-else class="pending-review-thumb pending-review-thumb--empty">无预览</div>
                <div class="pending-review-item-meta">
                  <div class="pending-review-file-name">{{ item.name }}</div>
                  <div class="pending-review-file-extra">
                    {{ item.annotationCount > 0 ? `${item.annotationCount} 个标注` : '暂无标注' }}
                    <span v-if="item.differenceCount" class="pending-review-separator">·</span>
                    <span v-if="item.differenceCount">{{ item.differenceCount }} 项差异</span>
                  </div>
                  <div v-if="item.integrationDecisionText" class="pending-review-decision">
                    {{ item.integrationDecisionText }}
                  </div>
                  <div v-if="item.differenceTypeLabels?.length" class="pending-review-tags">
                    <span
                      v-for="label in item.differenceTypeLabels"
                      :key="`${item.id}-${label}`"
                      class="pending-review-tag"
                    >
                      {{ label }}
                    </span>
                  </div>
                  <div v-if="item.reviewHint" class="pending-review-hint">
                    {{ item.reviewHint }}
                  </div>
                </div>
              </button>
            </div>
            <div v-else class="pending-review-empty">当前项目暂无待审核内容</div>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  items: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'select'])
</script>

<style scoped>
.pending-review-mask {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pending-review-panel {
  width: min(920px, calc(100vw - 40px));
  max-height: calc(100vh - 80px);
  background: #ffffff;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pending-review-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pending-review-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.pending-review-close {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: #f3f4f6;
  color: #374151;
  font-size: 20px;
  cursor: pointer;
}

.pending-review-body {
  padding: 18px 20px 22px;
  overflow: auto;
}

.pending-review-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}

.pending-review-item {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  padding: 8px;
  cursor: pointer;
}

.pending-review-thumb {
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  border-radius: 10px;
  display: block;
}

.pending-review-thumb--empty {
  background: #f3f4f6;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pending-review-item-meta {
  margin-top: 8px;
}

.pending-review-file-name {
  font-size: 13px;
  color: #111827;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pending-review-file-extra {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.pending-review-separator {
  margin: 0 4px;
}

.pending-review-decision {
  display: inline-flex;
  margin-top: 7px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #fff7ed;
  color: #c2410c;
  font-size: 12px;
  font-weight: 700;
}

.pending-review-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 7px;
}

.pending-review-tag {
  padding: 3px 7px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 11px;
  line-height: 1.2;
}

.pending-review-hint {
  margin-top: 7px;
  color: #475569;
  font-size: 12px;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pending-review-empty {
  color: #6b7280;
  padding: 18px 0;
  text-align: center;
}
</style>
