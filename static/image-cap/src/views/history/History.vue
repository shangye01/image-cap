<template>
  <!-- DAM 空间模板 -->
  <div class="dam-space-container gd-dam-space__space">
    <!-- 空间头部 -->
    <div
      class="gd-dam-space__index__space-header"
      style="align-items: center; margin-bottom: 8px; min-height: 40px"
    >
      <div class="gd-dam-space__index__space-header-left"></div>
      <div class="gd-dam-space__index__space-header-right">
        <!-- 邀请成员按钮 -->
        <button type="button" class="gda-btn gda-btn-sm">
          <svg
            role="img"
            aria-label="invite"
            focusable="false"
            data-icon="invite"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            class="gdesign-icon gdesign-icon-invite"
          >
            <path
              fill-rule="evenodd"
              clip-rule="evenodd"
              d="M11.865 4c-.735 0-1.445.3-1.97.84a2.95 2.95 0 0 0-.827 2.056c0 .383.073.762.215 1.115s.35.672.611.94c.26.268.57.48.907.623a2.71 2.71 0 0 0 2.128 0c.338-.144.646-.355.907-.623.26-.268.468-.587.61-.94.143-.353.216-.732.216-1.115 0-.775-.3-1.514-.826-2.055A2.75 2.75 0 0 0 11.865 4m-3.046-.205A4.25 4.25 0 0 1 11.865 2.5a4.25 4.25 0 0 1 3.046 1.295 4.45 4.45 0 0 1 1.251 3.1c0 .575-.11 1.145-.324 1.676a4.4 4.4 0 0 1-.927 1.426 4.3 4.3 0 0 1-1.395.957 4.21 4.21 0 0 1-3.302 0 4.3 4.3 0 0 1-1.395-.957 4.4 4.4 0 0 1-.927-1.426 4.5 4.5 0 0 1-.324-1.675c0-1.16.447-2.275 1.251-3.101M2.5 18.875c0-3.271 2.585-5.958 5.818-5.958h4.054v1.5H8.318C5.952 14.417 4 16.393 4 18.875v1.333h8.372v1.5H2.5zm16.196-.292H22v-1.5h-3.304v-3.416h-1.5v3.416h-3.304v1.5h3.304V22h1.5z"
              fill="currentColor"
            ></path>
          </svg>
          <span class="gda-badge">
            <span>邀请成员</span>
            <sup title="1" class="gda-scroll-number gda-badge-dot" data-show="true"></sup>
          </span>
        </button>

        <!-- 添加按钮 -->
        <div class="gd-dam-space__index__add-button">
          <button
            id="add-file-button"
            type="button"
            class="gda-btn gda-btn-primary gda-btn-sm gda-dropdown-trigger"
          >
            <svg
              role="img"
              aria-label="add"
              focusable="false"
              data-icon="add"
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              class="gdesign-icon gdesign-icon-add"
            >
              <path
                fill-rule="evenodd"
                clip-rule="evenodd"
                d="M11.25 12.75V21h1.5v-8.25H21v-1.5h-8.25V3h-1.5v8.25H3v1.5z"
                fill="currentColor"
              ></path>
            </svg>
            <span>添加</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 资产布局容器 -->
    <div
      class="dam-space-assets-layout-container gd-dam-space__layout-container__assets-layout-container"
    >
      <div
        class="dam-space-assets-layout-container gd-dam-space__assets-layout__assets-layout assets-layout-rename-container"
        style="height: 518.4px"
      >
        <!-- 筛选器和选项卡 -->
        <div
          class="dam-space-filter-container gda-row gd-dam-space__index__search-bar gd-dam-space__index__is-All"
        >
          <!-- 分类、颜色、类型、标签、时间筛选 -->
          <div class="gd-dam-space__index__category-container"></div>
          <div class="gd-dam-space__index__origin-filter-container gda-col">
            <div
              class="gda-tabs gda-tabs-top gda-tabs-small gda-tabs-line gda-tabs-no-animation gd-dam-space__index__tab-container"
            >
              <div
                role="tablist"
                class="gda-tabs-bar gda-tabs-top-bar gda-tabs-small-bar gda-tabs-bar-compact gda-tabs-bar-emphasize"
              >
                <div class="gda-tabs-nav-container">
                  <span class="gda-tabs-tab-prev gda-tabs-tab-btn-disabled"></span>
                  <span class="gda-tabs-tab-next gda-tabs-tab-btn-disabled"></span>
                  <div class="gda-tabs-nav-wrap">
                    <div class="gda-tabs-nav-scroll">
                      <div class="gda-tabs-nav gda-tabs-nav-animated">
                        <div>
                          <div role="tab" class="gda-tabs-tab-active gda-tabs-tab">全部 (0)</div>
                          <div role="tab" class="gda-tabs-tab">作品</div>
                          <div role="tab" class="gda-tabs-tab">我上传的</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="gda-tabs-content gda-tabs-content-no-animated gda-tabs-top-content">
                <div role="tabpanel" class="gda-tabs-tabpane gda-tabs-tabpane-active"></div>
                <div role="tabpanel" class="gda-tabs-tabpane gda-tabs-tabpane-inactive"></div>
                <div role="tabpanel" class="gda-tabs-tabpane gda-tabs-tabpane-inactive"></div>
              </div>
            </div>
          </div>

          <!-- 筛选工具组 -->
          <div class="gda-col gd-dam-space__index__search-bar--tools">
            <!-- 颜色筛选 -->
            <div class="gda-space-item">
              <div class="gd-dam-components__select-dropdown__select gda-dropdown-trigger">
                <section class="dam-selector gd-dam-components__color-filter__color-filter">
                  <span class="gd-dam-components__color-filter__color-filter--title">颜色</span>
                  <svg class="gdesign-icon gdesign-icon-arrow-down-small"></svg>
                </section>
              </div>
            </div>

            <!-- 类别筛选 -->
            <div class="gda-space-item">
              <div class="gd-dam-components__select-dropdown__select gda-dropdown-trigger">
                <div class="dam-selector gd-dam-components__select-result__select-result">
                  <span>类别</span>
                  <svg class="gdesign-icon gdesign-icon-arrow-down-small"></svg>
                </div>
              </div>
            </div>

            <!-- 类型筛选 -->
            <div class="gda-space-item">
              <div class="gd-dam-components__select-dropdown__select gda-dropdown-trigger">
                <div class="dam-selector gd-dam-components__select-result__select-result">
                  <span>类型</span>
                  <svg class="gdesign-icon gdesign-icon-arrow-down-small"></svg>
                </div>
              </div>
            </div>

            <!-- 标签筛选 -->
            <div class="gda-space-item">
              <div class="gd-dam-components__select-dropdown__select gda-dropdown-trigger">
                <div class="dam-selector gd-dam-components__select-result__select-result">
                  <span>标签</span>
                  <svg class="gdesign-icon gdesign-icon-arrow-down-small"></svg>
                </div>
              </div>
            </div>

            <!-- 时间筛选 -->
            <div class="gda-space-item">
              <div class="gd-dam-components__date-filter__date-filter">
                <div class="gd-dam-components__date-filter__select-result-container">
                  <div class="dam-selector gd-dam-components__select-result__select-result">
                    <span>添加时间</span>
                    <svg class="gdesign-icon gdesign-icon-arrow-down-small"></svg>
                  </div>
                </div>
                <span class="gda-calendar-picker gda-calendar-picker-small">
                  <span class="gda-calendar-picker-input gda-input gda-input-sm">
                    <input readonly placeholder="开始日期" />
                    <span class="gda-calendar-range-picker-separator"> ~ </span>
                    <input readonly placeholder="结束日期" />
                    <span class="gda-calendar-picker-icon"></span>
                  </span>
                </span>
              </div>
            </div>

            <!-- 显示子文件夹 -->
            <div class="gda-space-item">
              <div class="gd-dam-space__index__show-children">
                <button type="button" role="switch" class="gda-switch gda-switch-small">
                  <span class="gda-switch-inner"></span>
                </button>
                <span class="gd-dam-space__index__tip">显示子文件夹内容</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div class="gd-dam-space__assets-layout__empty-container" style="height: 454.4px">
          <div class="gd-dam-components__empty__empty">
            <img
              src="https://cdn.dancf.com/fe-assets/20231129/bf4141e10f461a7a82d257df49119b46.svg"
              alt="empty"
            />
            <div class="description">
              <p class="mt-0 mx-0 mb-12 text-16px font-weight-bold text-primary">
                拖放文件到这里，开始云端作图
              </p>
              <span class="text-14px text-tertiary">点击上传文件，支持上传本地文件</span>
              <div class="flex grid-items-center mt-24 mx-0 mb-100">
                <div class="gd-dam-components__drop-upload__drop-upload">
                  <button type="button" class="w-124 gda-btn gda-btn-primary gda-btn-sm">
                    上传文件
                  </button>
                  <input type="file" hidden multiple />
                </div>
                <div class="ml-16">
                  <button type="button" class="gda-btn gda-btn-primary gda-btn-sm">
                    从「稿定」导入
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 拖拽上传区 -->
    <div class="gd-dam-space__space__drop-area">
      <div class="gd-dam-space__space__drop-tip">
        <button type="button" class="gda-btn gda-btn-primary">上传到“我的空间”</button>
      </div>
      <div class="gd-dam-components__drop-upload__drop-upload">
        <input type="file" hidden multiple />
      </div>
    </div>
  </div>
</template>
