import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
 
// // 导入视图组件

// import AnnotateView from '../views/AnnotateView.vue'
// import TrainingView from '../views/TrainingView.vue'
// import TaskListView from '../views/TaskListView.vue'
// import ProfileView from '../views/ProfileView.vue'

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
     
    /* ========= 需要登录的路由 ========= */
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
        {
          path: 'profile',
          name: 'app-profile',
          component: () => import('@/views/profile/Profile.vue')
        }
      ]
    },
    
    // /* ========= 独立功能路由（需要登录） ========= */
    // {
    //   path: '/annotate',
    //   name: 'annotate',
    //   component: AnnotateView,
    //   meta: { requiresAuth: true }
    // },
    // {
    //   path: '/tasks',
    //   name: 'tasks',
    //   component: TaskListView,
    //   meta: { requiresAuth: true }
    // },
    // {
    //   path: '/training',
    //   name: 'training',
    //   component: TrainingView,
    //   meta: { requiresAuth: true }
    // },
    // {
    //   path: '/profile',
    //   name: 'profile',
    //   component: ProfileView,
    //   meta: { requiresAuth: true }
    // }
  ]
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  // 检查路由是否需要登录
  if (to.meta.requiresAuth && !userStore.isLogin) {
    // 未登录跳回首页
    next('/')
  } else {
    next()
  }
})

export default router