import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import store from "./store";
import VueToastr2 from "vue-toastr-2";

import "bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "vue-toastr-2/dist/vue-toastr-2.min.css";

window.toastr = require("toastr");

Vue.config.productionTip = false;

Vue.use(VueToastr2);

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount("#app");
