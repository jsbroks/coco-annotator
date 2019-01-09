<template>
  <div class="bg-light">
    <div style="padding-top: 55px" />
    <div class="album py-5 container" style="overflow: auto; height: calc(100vh - 55px)">
      <div class="row">
        <div class="col-sm text-left">
          <!-- Change this section to whatever you would like -->
          <h1>COCO Annotator</h1>
          <hr>
          <div v-if="totalUsers === 0">
            <h5>You have successfully installed COCO Annotator!</h5>
            <p>Use the registeration to create an admin account</p>
            <p>
              If you have any questions please checkout the
              <a href="https://github.com/jsbroks/coco-annotator/wiki">wiki</a> before
              posting an <a href="https://github.com/jsbroks/coco-annotator/issues">issues</a>.
            </p>
          </div>
          <div v-else>
            <p>
              COCO Annotator is a web-based image annotation tool designed for versatility and efficiently
              label images to create training data for image localization and object detection.
              <br><br>
              Login to create datasets.
              <br><br>
              Find out more <a href="https://github.com/jsbroks/coco-annotator">Github</a>
            </p>
          </div>
          <!-- End of section -->
        </div>
        <div class="col-sm">
          <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item" v-show="totalUsers !== 0">
              <a class="nav-link"
                 :class="{ active: tab === 'login'}"
                 id="home-tab"
                 data-toggle="tab"
                 href="#login"
                 role="tab"
                 aria-controls="home"
                 aria-selected="true"
                 @click="tab = 'login'"
              >
                Login
              </a>
            </li>
            <li class="nav-item" v-show="showRegistrationForm">
              <a class="nav-link"
                 :class="{ active: tab === 'register'}"
                 id="contact-tab"
                 data-toggle="tab"
                 href="#register"
                 role="tab"
                 aria-controls="contact"
                 aria-selected="false" @click="tab = 'register'"
                 ref="registerTab"
              >
                Register
              </a>
            </li>
          </ul>
          <div class="tab-content panel border-bottom border-right border-left text-left">
            <div class="tab-pane fade show active" id="login" role="tabpanel" aria-labelledby="login-tab">
              <form>
                <div class="form-group">
                  <label>Username</label>
                  <input v-model="loginForm.username" type="text" class="form-control" >
                </div>
                <div class="form-group">
                  <label >Password</label>
                  <input v-model="loginForm.password" type="password" class="form-control">
                </div>
                <div class="form-check">
                  <input v-model="loginForm.remember" type="checkbox" class="form-check-input">
                  <label class="form-check-label">Remember me</label>
                </div>
                <button type="submit" class="btn btn-primary btn-block" :class="{ disabled: !loginValid }" style="margin-top: 10px" @click="loginUser">
                  Login
                </button>
              </form>
            </div>
            <div class="tab-pane fade" id="register" role="tabpanel" aria-labelledby="register-tab">
              <div v-if="!showRegistrationForm">
                You are not allowed to register accounts
              </div>
              <form v-else>
                <div class="form-group" novalidate="">
                  <label>Full Name <span class="text-mute">(Optional)</span></label>
                  <input v-model="registerForm.name" type="text" class="form-control">
                </div>
                <div class="form-group" :class="{'was-validated': usernameIsValid(registerForm.username)}">
                  <label>Username</label>
                  <input v-model="registerForm.username" type="text" class="form-control">
                </div>
                <div class="form-group" :class="{'was-validated': registerForm.password.length > 4 }" required>
                  <label>Password</label>
                  <input v-model="registerForm.password" type="password" class="form-control">
                </div>
                <div class="form-group" :class="{'was-validated': registerForm.password === registerForm.confirmPassword && registerForm.password.length > 0}">
                  <label>Confirm Password</label>
                  <input v-model="registerForm.confirmPassword" type="password" class="form-control">
                </div>
                <div class="form-check">
                  <input v-model="registerForm.remember" type="checkbox" class="form-check-input">
                  <label class="form-check-label">Remember me</label>
                </div>
                <button type="submit" class="btn btn-primary btn-block" :class="{ disabled: !registerValid }" style="margin-top: 10px" @click="registerUser">
                  Register
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
      tab: "login",
      registerForm: {
        enabled: true,
        name: "",
        username: "",
        password: "",
        confirmPassword: "",
        remember: false
      },
      loginForm: {
        username: "",
        password: "",
        remember: false
      }
    };
  },
  methods: {
    ...mapActions("user", ["register", "login"]),
    ...mapMutations("info", ["increamentUserCount"]),
    registerUser(event) {
      event.preventDefault();
      if (!this.registerValid) return;

      let data = {
        user: this.registerForm,
        successCallback: () => {
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
    loginUser(event) {
      event.preventDefault();
      if (!this.loginValid) return;

      let data = {
        user: this.loginForm,
        successCallback: () => this.$router.push(this.redirect),
        errorCallback: error =>
          this.axiosReqestError("User Login", error.response.data.message)
      };
      this.login(data);
    },
    usernameIsValid(username) {
      return /^[0-9a-zA-Z_.-]+$/.test(username);
    }
  },
  computed: {
    registerValid() {
      if (!this.usernameIsValid(this.registerForm.username)) return false;
      if (this.registerForm.password.length < 5) return false;
      if (this.registerForm.password !== this.registerForm.confirmPassword)
        return false;

      return true;
    },
    loginValid() {
      if (!this.usernameIsValid(this.loginForm.username)) return false;
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
    }
  },
  watch: {
    totalUsers(users) {
      if (users === 0) {
        this.$refs.registerTab.click();
      }
    }
  }
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
</style>
