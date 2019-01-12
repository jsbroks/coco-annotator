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
    ...mapMutations("info", ["getServerInfo"]),
    toAuthPage() {
      this.$router.push({
        name: "authentication"
      });
    }
  },
  data() {
    return { loader: null };
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
    },
    loading() {
      return this.$store.state.info.loading;
    }
  },
  watch: {
    loading() {
      if (!this.loading && this.loader != null) {
        this.loader.hide();
      }
    },
    loginRequired: {
      handler(newValue) {
        if (newValue) {
          this.toAuthPage();
        } else {
          if (this.$router.name == "authentication") {
            this.$router.push({
              name: "datasets"
            });
          }
        }
      },
      immediate: true
    }
  },
  mounted() {
    if (this.$route.name.toLowerCase() !== "annotate") {
      this.loader = this.$loading.show({
        height: 100
      });
    }
  },
  created() {
    this.setUserInfo();
    this.getServerInfo();
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
