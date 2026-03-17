import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

const routes = [
  {
    path: "/",
    name: "home",
    component: HomeView,
  },
  {
    path: "/upload",
    name: "upload",
    component: () => import("../views/UploadView.vue"),
  },
  {
    path: "/reports",
    name: "reports",
    component: () => import("../views/ReportsView.vue"),
  },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
