import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/home/Home.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/Login.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/auth/Register.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/invite/:token',
      name: 'invite-accept',
      component: () => import('@/views/project/InviteAcceptView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/app',
      component: () => import('@/views/project/Layout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/app/guide' },
        { path: 'guide', name: 'guide', component: () => import('@/views/guide/CreateGuide.vue') },
        { path: 'project', name: 'project', component: () => import('@/views/project/ProjectContent.vue') },
        {
          path: 'publish',
          name: 'publish',
          component: () => import('@/views/project/ProjectContent.vue'),
          meta: { requiresAuth: true },
        },

        { path: 'annotate', name: 'annotate', component: () => import('@/views/annotate/AnnotateView.vue') },
        { path: 'tasks', name: 'tasks', component: () => import('@/views/tasks/TaskListView.vue') },
        { path: 'training', name: 'training', component: () => import('@/views/training/TrainingView.vue') },
        { path: 'profile', name: 'profile', component: () => import('@/views/profile/ProfileView.vue') },
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLogin) {
    next('/login')
    return
  }
  
  if ((to.path === '/login' || to.path === '/register') && userStore.isLogin) {
    next('/app/guide')
    return
  }

  next()
})

export default router
