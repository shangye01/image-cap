import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    /* ========= 公开路由（无需登录） ========= */
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/home/Home.vue'),
      meta: { requiresAuth: false }
    },
    
    /* ========= 需要登录的路由（带 Layout 布局） ========= */
    {
      path: '/app',
      component: () => import('@/views/project/Layout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/app/guide'
        },
        {
          path: 'guide',
          name: 'guide',
          component: () => import('@/views/guide/CreateGuide.vue')
        },
        {
          path: 'project',
          name: 'project',
          component: () => import('@/views/project/ProjectContent.vue')
        },
        {
          path: 'history',
          name: 'history',
          component: () => import('@/views/history/History.vue')
        },
        // 独立功能路由改为子路由
        {
          path: 'annotate',
          name: 'annotate',
          component: () => import('@/views/annotate/AnnotateView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/views/tasks/TaskListView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'training',
          name: 'training',
          component: () => import('@/views/training/TrainingView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/profile/ProfileView.vue'),
          meta: { requiresAuth: true }
        }
      ]
    }
  ]
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth && !userStore.isLogin) {
    next('/')
  } else {
    next()
  }
})

export default router