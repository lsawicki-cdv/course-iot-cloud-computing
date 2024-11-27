import { createRouter, createWebHistory } from 'vue-router'
import MainView from '@/views/MainView.vue'
import LineDiagramView from '@/views/LineDiagramView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Main',
      component: MainView
    },
    {
      path: '/diagram/line',
      name: 'LineDiagram',
      component: LineDiagramView
    }
  ]
})

export default router
