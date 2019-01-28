<template>
  <nav class="navbar navbar-expand-lg navbar-dark fixed-top">
    <a class="navbar-brand" href="/">
      <strong>{{ name }}</strong>
      <span class="subscript">{{ version }}</span>
    </a>

    <button
      class="navbar-toggler"
      type="button"
      data-toggle="collapse"
      data-target="#navbarSupportedContent"
      aria-controls="navbarSupportedContent"
      aria-expanded="false"
      aria-label="Toggle navigation"
    >
      <span class="navbar-toggler-icon" />
    </button>

    <div class="collapse navbar-collapse" id="navbarSupportedContent">
      <ul class="navbar-nav mr-auto">
        <li class="nav-item" :class="{ active: $route.name === 'datasets' }">
          <RouterLink class="nav-link" to="/datasets">Datasets</RouterLink>
        </li>
        <li class="nav-item" :class="{ active: $route.name === 'categories' }">
          <RouterLink class="nav-link" to="/categories">Categories</RouterLink>
        </li>
        <li class="nav-item" :class="{ active: $route.name === 'undo' }">
          <RouterLink class="nav-link" to="/undo">Undo</RouterLink>
        </li>
        <li
          v-show="$store.getters['user/isAdmin']"
          class="nav-item"
          :class="{ active: $route.name === 'admin' }"
        >
          <RouterLink class="nav-link" to="/admin/panel">Admin</RouterLink>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/api">API</a>
        </li>
        <li class="nav-item">
          <a
            class="nav-link"
            href="https://github.com/jsbroks/coco-annotator/wiki"
            >Help</a
          >
        </li>
      </ul>
      <Status />
      <User v-if="loginEnabled" />
    </div>
  </nav>
</template>

<script>
import User from "@/components/User";
import Status from "@/components/Status";

export default {
  name: "NavBar",
  components: { Status, User },
  computed: {
    version() {
      return this.$store.state.info.version;
    },
    loginEnabled() {
      return this.$store.state.info.loginEnabled;
    },
    name() {
      return this.$store.state.info.name;
    }
  }
};
</script>

<style scoped>
.subscript {
  padding: 10px;
  font-size: 10px;
  color: lightgray;
}

.navbar {
  background-color: #383c4a;
}
</style>
