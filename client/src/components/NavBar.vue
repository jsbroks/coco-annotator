<template>
  <nav class="navbar navbar-expand-lg navbar-dark fixed-top">
    
    <i class="fa fa-circle" :style="{ color: color }" style="padding: 0 10px; font-size: 10px" v-tooltip="$tr('status', backendStatus)"></i>

    <RouterLink class="navbar-brand" to="/">
      <strong>{{ name }}</strong>
      <span class="subscript">{{ version }}</span>
    </RouterLink>

    <button
      class="navbar-toggler"
      type="button"
      data-bs-toggle="collapse"
      data-bs-target="#navbarSupportedContent"
      aria-controls="navbarSupportedContent"
      aria-expanded="false"
      aria-label="Toggle navigation"
    >
      <span class="navbar-toggler-icon" />
    </button>

    <div class="collapse navbar-collapse" id="navbarSupportedContent">
      <ul class="navbar-nav me-auto">
        <li class="nav-item" :class="{ active: $route.name === 'datasets' || $route.name === 'dataset' }">
          <RouterLink class="nav-link" to="/datasets">{{ $t('navBar.datasets') }}</RouterLink>
        </li>
        <li
          class="nav-item"
          v-show="$route.name === 'annotate'"
          :class="{ active: $route.name === 'annotate' }"
        >
          <RouterLink
            class="nav-link"
            :to="`/dataset/${dataset.id}`"
          >
            {{ dataset.name }}
          </RouterLink>
        </li>
        <li class="nav-item" :class="{ active: $route.name === 'categories' }">
          <RouterLink class="nav-link" to="/categories">{{ $t('navBar.categories') }}</RouterLink>
        </li>
        <li v-if="canPage('activity')" class="nav-item" :class="{ active: $route.name === 'activity' }">
          <RouterLink class="nav-link" to="/activity">{{ $t('navBar.activity') }}</RouterLink>
        </li>
        <li v-if="canPage('models')" class="nav-item" :class="{ active: $route.name === 'models' }">
          <RouterLink class="nav-link" to="/models">{{ $t('navBar.models') }}</RouterLink>
        </li>
        <li v-if="canPage('tasks')" class="nav-item" :class="{ active: $route.name === 'tasks' }">
          <RouterLink class="nav-link" to="/tasks">{{ $t('navBar.tasks') }}</RouterLink>
        </li>
        <li v-if="canPage('train')" class="nav-item" :class="{ active: $route.name === 'train' }">
          <RouterLink class="nav-link" to="/train">{{ $t('navBar.train') }}</RouterLink>
        </li>
        <li v-if="canPage('terminal')" class="nav-item" :class="{ active: $route.name === 'terminal' }">
          <RouterLink class="nav-link" to="/terminal">{{ $t('navBar.terminal') }}</RouterLink>
        </li>
        <li
          v-show="$store.getters['user/can']('manage_users')"
          class="nav-item"
          :class="{ active: $route.name === 'admin' }"
        >
          <RouterLink class="nav-link d-none d-xl-block" to="/admin/panel">{{ $t('navBar.admin') }}</RouterLink>
        </li>
        <li class="nav-item d-none d-xl-block">
          <a class="nav-link" href="/api">API</a>
        </li>
        <li class="nav-item d-none d-xl-block">
          <a
            class="nav-link"
            :href="docsUrl" target="_blank" rel="noopener"
            >{{ $t('navBar.help') }}</a
          >
        </li>
      </ul>
      <Status class="nav-link left" />
      <HelpInbox v-if="$store.state.user.user && loginEnabled" class="me-2" />
      <LanguageSwitcher />
      <User class="nav-link left" v-if="loginEnabled" />
    </div>
  </nav>
</template>

<script>
import User from "@/components/User.vue";
import Status from "@/components/Status.vue";
import LanguageSwitcher from "@/components/LanguageSwitcher.vue";
import HelpInbox from "@/components/HelpInbox.vue";
import { DOCS_URL } from "@/links";

export default {
  name: "NavBar",
  components: { Status, User, LanguageSwitcher, HelpInbox },
  data() {
    return {
      docsUrl: DOCS_URL,
      color: "white",
      backendStatus: "Connection unknown"
    };
  },
  methods: {
    canPage(page) {
      return this.$store.getters["user/canPage"](page);
    }
  },
  computed: {
    version() {
      return this.$store.state.info.version;
    },
    loginEnabled() {
      return this.$store.state.info.loginEnabled;
    },
    name() {
      return this.$store.state.info.name;
    },
    socket() {
      return this.$store.state.info.socket;
    },
    dataset() {
      let dataset = this.$store.state.dataset;
      if (dataset == null) return { name: "", id: "" };

      return dataset;
    }
  },
  watch: {
    socket(connected) {
      if (connected == null) {
        this.color = "white";
        this.backendStatus = "Connection unknown";
        return;
      }

      if (connected) {
        this.color = "green";
        this.backendStatus = "Connected to backend";
      } else {
        this.color = "red";
        this.backendStatus = "Could not connect to backend";
      }
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

.left {
  padding: 0;
}
</style>
