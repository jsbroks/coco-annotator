<template>
  <div class="bg-light">
    <div style="padding-top: 55px" />
    <div class="album py-5 container" style="overflow: auto; height: calc(100vh - 55px)">
      <div class="row">
        <div class="col-sm text-left">
          <!-- Change this section to whatever you would like -->
          <h1>COCO Annotator</h1>
          <hr>
          <p>
            COCO Annotator is a web-based image annotation tool designed for versatility and efficiently
            label images to create training data for image localization and object detection.
            <br><br>
            Login to create datasets.
            <br><br>
            Find out more <a href="https://github.com/jsbroks/coco-annotator">Github</a>
          </p>
          <!---->
        </div>
        <div class="col-sm">
          <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item">
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
            <li class="nav-item" v-show="registerForm.enabled">
              <a class="nav-link"
                 :class="{ active: tab === 'register'}"
                 id="contact-tab"
                 data-toggle="tab"
                 href="#register"
                 role="tab"
                 aria-controls="contact"
                 aria-selected="false" @click="tab = 'register'"
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
                  <input v-model="loginForm.username" type="text" class="form-control">
                </div>
                <div class="form-group">
                  <label >Password</label>
                  <input v-model="loginForm.password" type="password" class="form-control">
                </div>
                <div class="form-check">
                  <input v-model="loginForm.remember" type="checkbox" class="form-check-input">
                  <label class="form-check-label">Remember me</label>
                </div>
                <button type="button" class="btn btn-primary btn-block" style="margin-top: 10px" @click="loginUser">
                  Submit
                </button>
              </form>
            </div>
            <div class="tab-pane fade" id="register" role="tabpanel" aria-labelledby="register-tab">
              <div v-if="!registerForm.enabled">
                You are not allowed to register accounts
              </div>
              <form v-else>
                <div class="form-group">
                  <label>Full Name</label>
                  <input v-model="registerForm.name" type="text" class="form-control">
                </div>
                <div class="form-group">
                  <label>Username</label>
                  <input v-model="registerForm.username" type="text" class="form-control">
                </div>
                <div class="form-group">
                  <label>Password</label>
                  <input v-model="registerForm.password" type="password" class="form-control">
                </div>
                <div class="form-group">
                  <label>Confirm Password</label>
                  <input v-model="registerForm.confirmPassword" type="password" class="form-control">
                </div>
                <div class="form-check">
                  <input v-model="registerForm.remember" type="checkbox" class="form-check-input">
                  <label class="form-check-label">Remember me</label>
                </div>
                <button type="button" class="btn btn-primary btn-block" style="margin-top: 10px" @click="registerUser">
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
import axios from "axios";
import toastrs from "@/mixins/toastrs";
import { mapActions } from "vuex";
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
    registerUser() {
      let data = {
        user: this.registerForm,
        successCallback: () => this.$router.push(this.redirect),
        errorCallback: error =>
          this.axiosReqestError(
            "User Registration",
            error.response.data.message
          )
      };
      this.register(data);
    },
    loginUser() {
      let data = {
        user: this.loginForm,
        successCallback: () => this.$router.push(this.redirect),
        errorCallback: error =>
          this.axiosReqestError("User Login", error.response.data.message)
      };
      this.login(data);
    }
  },
  computed: {
    registerValid() {
      return true;
    }
  }
};
</script>

<style scoped>
.panel {
  padding: 30px;
  background-color: white;
}
</style>
