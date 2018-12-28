<template>
  <div id="app">
    <NavBar v-show="showNavBar"/>
    <RouterView :key="$route.fullPath" />
  </div>
</template>

<script>
import NavBar from "@/components/NavBar";
import { mapMutations } from "vuex";

export default {
  name: "App",
  components: { NavBar },
  methods: {
    ...mapMutations("user", ["setUserInfo"]),
    toAuthPage() {
      let redirect = { name: this.$route.name, params: this.$route.params };
      this.$router.push({
        name: "authentication",
        params: { redirect: redirect }
      });
    }
  },
  computed: {
    showNavBar() {
      let notShow = ["authentication", "setup"];
      return notShow.indexOf(this.$route.name) === -1;
    },
    isAuthenticated() {
      return this.$store.state.user.isAuthenticated;
    },
    isAuthenticatePending() {
      return this.$store.state.user.isAuthenticatePending;
    },
    loginRequired() {
      if (this.isAuthenticatePending) {
        return false;
      }
      return !this.isAuthenticated;
    }
  },
  watch: {
    loginRequired(newValue) {
      if (newValue) {
        this.toAuthPage();
      }
    },
    "$route.name"() {
      if (this.loginRequired) {
        this.toAuthPage();
      }
    }
  },
  created() {
    this.setUserInfo();
  }
};
</script>

<style>
@import "./assets/tagsStyle.css";
@import "./assets/tooltip.css";

#app {
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  height: inherit;
  width: inherit;
  overflow: hidden;
}
</style>
