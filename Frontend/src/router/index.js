import { createRouter, createWebHistory } from "vue-router";

import viviendaRoutes from "@/modules/vivienda/router";

import { useAuthStore } from "@/stores/authStore";


const routes = [
  {
    path: "/",
    redirect: "/vivienda/landing",
  },

  ...viviendaRoutes,
];


const router = createRouter({
  history: createWebHistory(),
  routes,

  scrollBehavior() {
    return { top: 0 };
  },
});


router.beforeEach((to) => {
  const authStore = useAuthStore();

  if (to.meta?.requiresAuth && !authStore.user) {
    return {
      path: "/vivienda/login",
    };
  }

  return true;
});


router.afterEach((to) => {
  document.title = to.meta?.title || "Quantia";
});


export default router;