import Vue from "vue";
import Router from "vue-router";

import Home from "@/views/Home";
import About from "@/views/About";
import Annotator from "@/views/Annotator";
import Datasets from "@/views/Datasets";
import Categories from "@/views/Categories";
import Undo from "@/views/Undo";
import Dataset from "@/views/Dataset";

Vue.use(Router);

export default new Router({
  // mode: "history",
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
      path: "/categories",
      name: "categories",
      component: Categories
    },
    {
      path: "/undo",
      name: "undo",
      component: Undo
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
    }
  ]
});
