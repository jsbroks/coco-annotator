<template>
  <div id="app">
    <NavBar v-show="showNavBar" />
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
    ...mapMutations("info", ["getServerInfo", "socket"]),
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
    },
    socketConnection() {
      return this.$store.state.info.socket;
    }
  },
  watch: {
    loading() {
      if (!this.loading && this.loader != null) {
        this.loader.hide();
      }
    },
    socketConnection() {
      if (this.socketConnection) return;

      setTimeout(() => {
        if (this.socketConnection) return;
        let options = {
          positionClass: "toast-bottom-left"
        };

        this.$toastr.warning(
          "Connection lost to the backend",
          "Connection Lost",
          options
        );
      }, 1000);
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
  sockets: {
    connect() {
      this.socket(true);
    },
    disconnect() {
      this.socket(false);
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
