import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    /* ========= 登录前 ========= */
    {
      path: '/',
      component: () => import('@/views/home/Home.vue')
    },
    // {
    //   path: '/login',
    //   component: () => import('@/views/auth/Login.vue')
    // },
    // {
    //   path: '/register',
    //   component: () => import('@/views/auth/Register.vue')
    // },

    /* ========= 登录后系统 ========= */
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
          component: () => import('@/views/guide/CreateGuide.vue')
        },
        {
          path: 'project',
          component: () => import('@/views/project/ProjectContent.vue')
        },
        {
          path: 'history',
          component: () => import('@/views/history/History.vue')
        },
        {
          path: 'profile',
          component: () => import('@/views/profile/Profile.vue')
        }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLogin) {
    // 未登录跳回首页
    return '/'
  }
})


export default router
