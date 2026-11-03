<template>
  <div class="d-flex align-items-center my-2 my-lg-0" style="margin-right: 10px">
    <div class="dropdown show">
      <a
        class="btn btn-outline-light btn-sm dropdown-toggle"
        href="#"
        role="button"
        id="dropdownMenuLink"
        data-bs-toggle="dropdown"
        aria-haspopup="true"
        aria-expanded="false"
      >
        {{ display }}
      </a>

      <ul
        class="dropdown-menu dropdown-menu-end"
        aria-labelledby="dropdownMenuLink"
        role="menu"
      >
        <li>
          <a
            v-show="$store.getters['user/can']('manage_users')"
            class="dropdown-item"
            href="#"
          >
            <RouterLink class="route" to="/admin/panel">{{ $t('user.adminPanel') }}</RouterLink>
          </a>
        </li>
        <li>
          <a class="dropdown-item" href="#">
            <RouterLink class="route" to="/user">{{ $t('user.userSettings') }}</RouterLink>
          </a>
        </li>
        <li>
          <a class="dropdown-item" href="#" @click="logoutButton">{{ $t('user.logout') }}</a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import { mapActions } from "vuex";

export default {
  name: "User",
  methods: {
    ...mapActions("user", ["logout"]),
    logoutButton() {
      if (this.$route.name === "annotate") {
        this.$router.replace({ name: "datasets" }, this.logout);
        return;
      }
      this.logout();
    }
  },
  computed: {
    user() {
      return this.$store.state.user.user;
    },
    display() {
      if (!this.user) return "";
      return this.user.name || this.user.username || "";
    }
  }
};
</script>

<style scoped>
a:hover {
  text-decoration: none;
}
.route {
  color: black;
}
</style>
