import "intersection-observer";

import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import store from "./store";
import VueToastr2 from "vue-toastr-2";
import paper from "paper";
import VTooltip from "v-tooltip";
import Loading from "vue-loading-overlay";
import VueTouch from 'vue-touch'
import VueSocketIO from "vue-socket.io";
import { VLazyImagePlugin } from "v-lazy-image";

import "bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "vue-toastr-2/dist/vue-toastr-2.min.css";
import "vue-loading-overlay/dist/vue-loading.css";

Vue.config.productionTip = false;

paper.install(window);

window.toastr = require("toastr");

Vue.use(VueToastr2);
Vue.use(VTooltip);
Vue.use(Loading);
Vue.use(VLazyImagePlugin);
Vue.use(
  new VueSocketIO({
    debug: true,
    connection: window.location.origin
  })
);
Vue.use(VueTouch,{name:'v-touch'});

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount("#app");
