import Vue from "vue";
import Router from "vue-router";

import Home from "@/views/Home.vue";
import About from "@/views/About.vue";
import Annotator from "@/views/Annotator.vue";
import Datasets from "@/views/Datasets.vue";

Vue.use(Router);

export default new Router({
  routes: [
    {
      path: "/",
      name: "home",
      component: Home
    },
    {
      path: "/about",
      name: "about",
      component: About
    },
    {
      path: "/datasets",
      name: "datasets",
      component: Datasets
    },
    {
      path: "/annotator",
      name: "annotator",
      component: Annotator
    }
  ]
});
