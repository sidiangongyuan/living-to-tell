import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dates'
    },
    {
      path: '/dates',
      name: 'dates',
      component: () => import('./features/dates/DatesView.vue')
    },
    {
      path: '/articles',
      name: 'articles',
      component: () => import('./features/articles/ArticlesView.vue')
    },
    {
      path: '/collections',
      name: 'collections',
      component: () => import('./features/collections/CollectionsView.vue')
    },
    {
      path: '/ai',
      name: 'ai',
      component: () => import('./features/ai/AiView.vue')
    },
    {
      path: '/library',
      name: 'library',
      component: () => import('./features/library/LibraryView.vue')
    },
    {
      path: '/motifs',
      name: 'motifs',
      component: () => import('./features/motifs/MotifsView.vue')
    },
    {
      path: '/ai-cards',
      name: 'ai-cards',
      component: () => import('./features/ai_cards/AiCardsView.vue')
    },
    {
      path: '/backup',
      name: 'backup',
      component: () => import('./features/backup/BackupView.vue')
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('./features/settings/SettingsView.vue')
    }
  ]
})

export default router
