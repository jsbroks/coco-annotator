<template>
  <div class="d-flex align-items-center my-2 my-lg-0 me-2">
    <div class="dropdown">
      <a
        class="btn btn-outline-light btn-sm dropdown-toggle"
        href="#"
        role="button"
        data-bs-toggle="dropdown"
        aria-expanded="false"
        :title="$t('nav.language')"
      >
        <i class="fa fa-globe" aria-hidden="true"></i>
        {{ current.label }}
      </a>
      <ul class="dropdown-menu dropdown-menu-end" role="menu">
        <li v-for="language in languages" :key="language.code">
          <a
            class="dropdown-item"
            :class="{ active: language.code === $i18n.locale }"
            href="#"
            @click.prevent="choose(language.code)"
          >
            {{ language.label }}
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import { LANGUAGES, setLocale } from "@/i18n";

export default {
  name: "LanguageSwitcher",
  data() {
    return { languages: LANGUAGES };
  },
  computed: {
    current() {
      return this.languages.find(l => l.code === this.$i18n.locale) || this.languages[0];
    }
  },
  methods: {
    choose(code) {
      setLocale(code);
    }
  }
};
</script>
