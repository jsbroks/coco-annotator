import { createRouter, createWebHashHistory } from "vue-router";
import Datasets from "@/views/Datasets.vue";
import Auth from "@/views/Auth.vue";
import PageNotFound from "@/views/PageNotFound.vue";

// The dataset list and sign-in come with the first load; every other page is
// downloaded the first time it is opened.
const About = () => import("@/views/About.vue");
const Annotator = () => import("@/views/Annotator.vue");
const AdminPanel = () => import("@/views/AdminPanel.vue");
const Categories = () => import("@/views/Categories.vue");
const Activity = () => import("@/views/Activity.vue");
const Models = () => import("@/views/Models.vue");
const Dataset = () => import("@/views/Dataset.vue");
const User = () => import("@/views/User.vue");
const Tasks = () => import("@/views/Tasks.vue");
const Review = () => import("@/views/Review.vue");
const Train = () => import("@/views/Train.vue");
const Terminal = () => import("@/views/Terminal.vue");

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: "/about",
      name: "about",
      component: About
    },
    {
      alias: "/",
      path: "/datasets",
      name: "datasets",
      component: Datasets
    },
    {
      path: "/categories",
      name: "categories",
      component: Categories
    },
    {
      path: "/activity",
      name: "activity",
      component: Activity,
      meta: { page: "activity" }
    },
    {
      path: "/models",
      name: "models",
      component: Models,
      meta: { page: "models" }
    },
    {
      path: "/trash",
      redirect: { path: "/activity", query: { group: "trash" } }
    },
    {
      path: "/undo",
      redirect: { path: "/activity", query: { group: "trash" } }
    },
    {
      path: "/annotate/:identifier",
      name: "annotate",
      component: Annotator,
      props: true
    },
    {
      path: "/dataset/:identifier",
      name: "dataset",
      component: Dataset,
      props: true
    },
    {
      path: "/review/:identifier",
      name: "quickReview",
      component: Review,
      props: true
    },
    {
      path: "/auth",
      name: "authentication",
      component: Auth,
      props: true
    },
    {
      path: "/user",
      name: "user",
      component: User
    },
    {
      path: "/admin/panel",
      name: "admin",
      component: AdminPanel,
      meta: { page: "manage_users" }
    },
    {
      path: "/tasks",
      name: "tasks",
      component: Tasks,
      meta: { page: "tasks" }
    },
    {
      path: "/train",
      name: "train",
      component: Train,
      meta: { page: "train" }
    },
    {
      path: "/terminal",
      name: "terminal",
      component: Terminal,
      meta: { page: "terminal" }
    },
    { path: "/:pathMatch(.*)*", component: PageNotFound }
  ]
});

// After an update the old page files are gone: a page opened from a tab that
// still runs the old version fails to load. Reload once to get the new one.
const RELOAD_KEY = "router/reloadedFor";
router.onError((error, to) => {
  const msg = String((error && error.message) || error);
  if (!/dynamically imported module|Importing a module script failed|Failed to fetch|error loading dynamically/i.test(msg)) return;
  let last = null;
  try {
    last = sessionStorage.getItem(RELOAD_KEY);
    sessionStorage.setItem(RELOAD_KEY, to.fullPath);
  } catch {
    // no storage: reload anyway (at most once per click)
  }
  if (last === to.fullPath) return;
  window.location.hash = to.fullPath;
  window.location.reload();
});
router.afterEach(() => {
  try {
    sessionStorage.removeItem(RELOAD_KEY);
  } catch {
    // ignore
  }
});

export default router;
