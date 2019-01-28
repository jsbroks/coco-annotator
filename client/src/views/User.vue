<template>
  <div>
    <div style="padding-top: 55px" />
    <div
      class="album py-5 bg-light"
      style="overflow: auto; height: calc(100vh - 55px)"
    >
      <div class="container">
        <h2 class="text-center">Hello, {{ displayName }}</h2>

        <br />
        <div style="text-align: left">
          <h4>Change Password</h4>
          <br />
          <form>
            <div class="form-group">
              <label>Current Password</label>
              <input
                v-model="changePassword.password"
                type="password"
                class="form-control"
                required
              />
            </div>
            <div class="form-group">
              <label>New Password</label>
              <input
                v-model="changePassword.new_password"
                :class="inputPasswordClasses(changePassword.new_password)"
                type="password"
                class="form-control"
                required
              />
              <div class="invalid-feedback">
                Minimum length of 5 characters.
              </div>
            </div>
            <div class="form-group">
              <label>Confirm Password</label>
              <input
                v-model="changePassword.confirm_password"
                :class="{
                  'is-valid':
                    changePassword.confirm_password.length > 0 &&
                    changePassword.confirm_password ===
                      changePassword.new_password
                }"
                type="password"
                class="form-control"
              />
            </div>
            <button
              type="submit"
              class="btn btn-primary btn-block"
              @click.prevent="changeUserPassword"
            >
              Submit
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import toastrs from "@/mixins/toastrs";
import { mapMutations } from "vuex";

export default {
  name: "AdminPanel",
  mixins: [toastrs],
  data() {
    return {
      changePassword: {
        password: "",
        new_password: "",
        confirm_password: ""
      }
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    changeUserPassword() {
      if (!this.validPassword(this.changePassword.new_password)) return;
      if (this.changePassword.password.length === 0) return;

      axios
        .post("/api/user/password", { ...this.changePassword })
        .then(() => {
          this.axiosReqestSuccess(
            "Changing Password",
            "Password has been changed"
          );
        })
        .catch(error => {
          this.axiosReqestError(
            "Changing Password",
            error.response.data.message
          );
        });
    },
    validPassword(password) {
      return password.length > 5;
    },
    inputPasswordClasses(password) {
      let isValid = password.length > 4;

      return {
        "is-invalid": !isValid && password.length != 0,
        "is-valid": isValid
      };
    }
  },
  computed: {
    user() {
      return this.$store.state.user.user;
    },
    displayName() {
      if (this.user == null) return "";
      if (this.user.name.length == 0) return this.user.username;

      return this.user.name;
    }
  },
  watch: {
    limit: "updatePage"
  },
  created() {}
};
</script>

<style scoped>
.remove-top-border {
  border: none !important;
}

.fa {
  margin: 0;
  padding: 2px;
}

.edit-icon:hover {
  color: green;
}

.delete-icon:hover {
  color: red;
}
</style>
