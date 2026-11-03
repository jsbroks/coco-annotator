<template>
  <div class="bg-light">
    <div style="padding-top: 55px" />
    <div
      class="album py-5 container"
      style="overflow: auto; height: calc(var(--vh) - 55px)"
    >
      <div class="row">
        <div class="col-sm text-start">
          <!-- Change this section to whatever you would like -->
          <h1>COCO Annotator</h1>
          <hr />
          <div v-if="totalUsers === 0">
            <h3>{{ $t('auth.youHaveSuccessfullyInstalledCoco') }}</h3>
            <p>{{ $t('auth.useTheRegisterationFormTo') }}</p>
            <p>
              <i18n-t keypath="auth.questions" tag="span">
                <template #wiki><a :href="docsUrl" target="_blank" rel="noopener">{{ $t('auth.wiki') }}</a></template>
                <template #issues><a :href="issuesUrl" target="_blank" rel="noopener">{{ $t('auth.issues') }}</a></template>
              </i18n-t>
            </p>
          </div>
          <div v-else>
            <p>
              {{ $t('auth.description') }}
              <br /><br />
              {{ $t('auth.loginToCreate') }}
              <br /><br />
              {{ $t('auth.findOutMore') }}
              <a :href="repoUrl" target="_blank" rel="noopener">GitHub</a>
            </p>
          </div>
          <!-- End of section -->
        </div>
        <div class="col-sm">
          <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item" v-show="totalUsers !== 0">
              <a
                class="nav-link"
                :class="{ active: tab === 'login' }"
                id="home-tab"
                data-bs-toggle="tab"
                href="#login"
                role="tab"
                aria-controls="home"
                aria-selected="true"
                @click="tab = 'login'"
              >
                {{ $t('auth.login') }}
              </a>
            </li>
            <li class="nav-item" v-show="showRegistrationForm">
              <a
                class="nav-link"
                :class="{ active: tab === 'register' }"
                id="contact-tab"
                data-bs-toggle="tab"
                href="#register"
                role="tab"
                aria-controls="contact"
                aria-selected="false"
                @click="tab = 'register'"
                ref="registerTab"
              >
                {{ $t('auth.register') }}
              </a>
            </li>
          </ul>
          <div
            class="tab-content panel border-bottom border-end border-start text-start"
          >
            <div
              class="tab-pane fade show active"
              id="login"
              role="tabpanel"
              aria-labelledby="login-tab"
            >
              <form class="vld-parent" ref="loginForm">
                <div class="mb-3">
                  <label>{{ $t('auth.username') }}</label>
                  <input
                    v-model="loginForm.username"
                    type="text"
                    class="form-control"
                    required
                  />
                  <div class="invalid-feedback">{{ $t('auth.invalidUsernameFormat') }}</div>
                </div>
                <div class="mb-3">
                  <label>{{ $t('auth.password') }}</label>
                  <input
                    v-model="loginForm.password"
                    type="password"
                    class="form-control"
                  />
                </div>
                <button
                  type="submit"
                  class="btn btn-primary w-100"
                  :class="{ disabled: !loginValid }"
                  @click.prevent="loginUser"
                >
                  {{ $t('auth.login') }}
                </button>
              </form>
            </div>
            <div
              class="tab-pane fade"
              id="register"
              role="tabpanel"
              aria-labelledby="register-tab"
            >
              <div v-if="!showRegistrationForm">
                {{ $t('auth.youAreNotAllowedTo') }}
              </div>
              <form v-else class="vld-parent" ref="registerForm">
                <div class="mb-3" novalidate="">
                  <label
                    >{{ $t('auth.fullName') }} <span class="text-mute">{{ $t('auth.optional') }}</span></label
                  >
                  <input
                    v-model="registerForm.name"
                    type="text"
                    class="form-control"
                  />
                </div>

                <div class="mb-3">
                  <label>{{ $t('auth.username') }}</label>
                  <input
                    v-model="registerForm.username"
                    :class="inputUsernameClasses(registerForm.username)"
                    type="text"
                    class="form-control"
                    required
                  />
                  <div class="invalid-feedback">{{ $t('auth.invalidUsernameFormat') }}</div>
                </div>

                <div class="mb-3">
                  <label>{{ $t('auth.password') }}</label>
                  <input
                    v-model="registerForm.password"
                    :class="inputPasswordClasses(registerForm.password)"
                    type="password"
                    class="form-control"
                    required
                  />
                  <div class="invalid-feedback">
                    {{ $t('auth.minimumLengthOf5Characters') }}
                  </div>
                </div>

                <div class="mb-3">
                  <label>{{ $t('auth.confirmPassword') }}</label>
                  <input
                    v-model="registerForm.confirmPassword"
                    :class="{
                      'is-valid':
                        registerForm.confirmPassword.length > 0 &&
                        registerForm.confirmPassword === registerForm.password
                    }"
                    type="password"
                    class="form-control"
                  />
                </div>
                <button
                  type="submit"
                  class="btn btn-primary w-100"
                  :class="{ disabled: !registerValid }"
                  @click.prevent="registerUser"
                >
                  {{ $t('auth.register') }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import toastrs from "@/mixins/toastrs";
import { DOCS_URL, ISSUES_URL, REPO_URL } from "@/links";
import { mapActions, mapMutations } from "vuex";
export default {
  name: "Authentication",
  mixins: [toastrs],
  props: {
    redirect: {
      type: Object,
      default() {
        return { name: "datasets" };
      }
    }
  },
  data() {
    return {
      docsUrl: DOCS_URL,
      issuesUrl: ISSUES_URL,
      repoUrl: REPO_URL,
      tab: "login",
      registerForm: {
        loading: false,
        name: "",
        username: "",
        password: "",
        confirmPassword: ""
      },
      loginForm: {
        loading: false,
        username: "",
        password: ""
      }
    };
  },
  methods: {
    ...mapActions("user", ["register", "login"]),
    ...mapMutations("info", ["increamentUserCount"]),
    /**
     * Reigsters a user with provided infomation from login form
     */
    registerUser() {
      if (!this.registerValid) return;

      let loader = this.$loading.show({
        container: this.$refs.registerForm,
        color: "#383c4a"
      });

      let data = {
        user: this.registerForm,
        successCallback: () => {
          loader.hide();
          this.increamentUserCount();
          this.$router.push(this.redirect);
        },
        errorCallback: error =>
          this.axiosReqestError(
            "User Registration",
            error.response.data.message
          )
      };

      this.register(data);
    },
    /**
     * Login a user with provided infomation from login form
     */
    loginUser() {
      if (!this.loginValid) return;

      let loader = this.$loading.show({
        container: this.$refs.registerForm,
        color: "#383c4a"
      });

      let data = {
        user: this.loginForm,
        successCallback: () => {
          loader.hide();
          this.$router.push(this.redirect);
        },
        errorCallback: error =>
          this.axiosReqestError("User Login", error.response.data.message)
      };
      this.login(data);
    },
    /**
     * Returns boolean value if provide string is a valid username
     * @param {string} username
     * @returns {boolean} true if valid otherwise false
     */
    validUsername(username) {
      return /^[0-9a-zA-Z_.-]+$/.test(username);
    },
    /**
     * Returns boolean value if provide string is a valid password
     * @param {string} password
     * @returns {boolean} true if valid otherwise false
     */
    validPassword(password) {
      return password.length > 5;
    },
    /**
     * Returns classes to be applied to a username input field for validation
     * @param {string} username input username string
     * @returns {object} validation classes
     */
    inputUsernameClasses(username) {
      let isValid = this.validUsername(username);

      return {
        "is-invalid": !isValid && username.length != 0,
        "is-valid": isValid
      };
    },
    /**
     * Returns classes to be applied to a password input field for validation
     * @param {string} password input password string
     * @returns {object} validation classes
     */
    inputPasswordClasses(password) {
      let isValid = password.length > 4;

      return {
        "is-invalid": !isValid && password.length != 0,
        "is-valid": isValid
      };
    }
  },
  computed: {
    registerValid() {
      if (!this.validUsername(this.registerForm.username)) return false;
      if (this.registerForm.password.length < 5) return false;
      if (this.registerForm.password !== this.registerForm.confirmPassword)
        return false;

      return true;
    },
    loginValid() {
      if (!this.validUsername(this.loginForm.username)) return false;
      if (this.loginForm.password.length == 0) return false;
      return true;
    },
    totalUsers() {
      return this.$store.state.info.totalUsers;
    },
    allowRegistration() {
      return this.$store.state.info.allowRegistration;
    },
    showRegistrationForm() {
      return this.totalUsers == 0 || this.allowRegistration;
    },
    isAuthenticatePending() {
      return this.$store.state.user.isAuthenticatePending;
    }
  },
  watch: {
    totalUsers(users) {
      if (users === 0) {
        this.$refs.registerTab.click();
      }
    },
    isAuthenticatePending: {
      handler() {
        if (this.isAuthenticatePending) {
          this.$router.push({
            name: "datasets"
          });
        }
      },
      immediate: true
    }
  },
  mounted() {}
};
</script>

<style scoped>
.panel {
  padding: 30px;
  background-color: white;
}

.text-mute {
  font-size: 10px;
}

.btn-button {
  margin-top: 10px;
}
</style>
