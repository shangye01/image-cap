
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import VueKonva from 'vue-konva'  // 确保这行存在
import App from './App.vue'
import router from './router'
import VueECharts from 'vue-echarts'  // 添加

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)

app.use(createPinia())
app.use(VueKonva)  // 确保这行存在且顺序正确
app.component('v-chart', VueECharts)  // 全局注册
app.use(router)
app.use(ElementPlus)

app.mount('#app')


