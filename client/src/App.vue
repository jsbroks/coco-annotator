<template>
  <div id="app">
    <UpdateBanner ref="update" />
    <NavBar v-show="showNavBar" />
    <ForcePasswordChange v-if="mustChangePassword" :user="$store.state.user.user" />
    <template v-if="pageNeeded">
      <NoPageAccess v-if="pageBlocked" :page="pageNeeded" />
      <RouterView v-else-if="$store.state.user.user" :key="$route.fullPath" />
    </template>
    <RouterView v-else :key="$route.fullPath" />
  </div>
</template>

<script>
import NavBar from "@/components/NavBar.vue";
import NoPageAccess from "@/components/NoPageAccess.vue";
import ForcePasswordChange from "@/components/ForcePasswordChange.vue";
import UpdateBanner from "@/components/UpdateBanner.vue";
import { mapMutations } from "vuex";

export default {
  name: "App",
  components: { NavBar, NoPageAccess, ForcePasswordChange, UpdateBanner },
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
    /** Activity log, Models and Tasks need permission for non-admins */
    pageNeeded() {
      return (this.$route.meta && this.$route.meta.page) || null;
    },
    currentUsername() {
      const user = this.$store.state.user.user;
      return user ? user.username : null;
    },
    /** logged in with a password an admin chose: pick one before anything else */
    mustChangePassword() {
      const user = this.$store.state.user.user;
      return !!(user && user.must_change_password && this.$route.name !== "authentication");
    },
    pageBlocked() {
      if (!this.pageNeeded || !this.$store.state.user.user) return false;
      return !this.$store.getters["user/canPage"](this.pageNeeded);
    },
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
          this.$t("toast.connectionLostToTheBackend"),
          this.$t("toast.connectionLost"),
          options
        );
      }, 1000);
    },
    /** the socket joins the user's room when it connects: reconnect after logging in / out */
    currentUsername(now) {
      // join this user's room (pushed questions / answers): the socket may
      // have connected before logging in
      if (now && this.$socket) {
        this.$socket.emit("join_user", null, ok => {
          if (ok === false) {
            this.$socket.disconnect();
            this.$socket.connect();
          }
        });
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
  sockets: {
    connect() {
      this.socket(true);
      // a reconnect usually means the server restarted: maybe a new version
      if (this.$refs.update) this.$refs.update.check();
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

/* the visible height: on phones 100vh also counts what the browser's own
   bars (iPhone Safari's bottom toolbar) cover, so the end of a page could
   not be scrolled to */
:root {
  --vh: 100vh;
}
@supports (height: 100dvh) {
  :root {
    --vh: 100dvh;
  }
}
/* phones: room below the last thing on a page */
@media (max-width: 767.98px) {
  #app .page-container {
    padding-bottom: calc(32px + env(safe-area-inset-bottom, 0px)) !important;
  }
}

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
