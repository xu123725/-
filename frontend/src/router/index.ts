import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import QBank from '../views/QBank.vue'
import Chat from '../views/Chat.vue'
import Exam from '../views/Exam.vue'
import WrongBook from '../views/WrongBook.vue'
import Settings from '../views/Settings.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: Dashboard
    },
    {
      path: '/qbank',
      name: 'QBank',
      component: QBank
    },
    {
      path: '/exam',
      name: 'Exam',
      component: Exam
    },
    {
      path: '/wrongbook',
      name: 'WrongBook',
      component: WrongBook
    },
    {
      path: '/chat',
      name: 'Chat',
      component: Chat
    },
    {
      path: '/settings',
      name: 'Settings',
      component: Settings
    }
  ]
})

export default router
