<template>
  <div class="form-inline my-2 my-lg-0" style="margin-right: 10px">
    <div class="dropdown show">
      <a
        class="btn-outline-light btn-sm dropdown-toggle"
        href="#"
        role="button"
        id="dropdownMenuLink"
        data-toggle="dropdown"
        aria-haspopup="true"
        aria-expanded="false"
      >
        {{ display }}
      </a>

      <ul
        class="dropdown-menu dropdown-menu-right"
        aria-labelledby="dropdownMenuLink"
        role="menu"
      >
        <li>
          <a
            v-show="$store.getters['user/isAdmin']"
            class="dropdown-item"
            href="#"
          >
            <RouterLink class="route" to="/admin/panel">Admin Panel</RouterLink>
          </a>
        </li>
        <li>
          <a class="dropdown-item" href="#">
            <RouterLink class="route" to="/user">User Settings</RouterLink>
          </a>
        </li>
        <li>
          <a class="dropdown-item" href="#" @click="logoutButton">Logout</a>
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
      return this.user.name.length === 0 ? this.user.username : this.user.name;
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
