<template>
  <div>
    <div style="padding-top: 55px" />
    <div
      class="album py-5 bg-light"
      style="overflow: auto; height: calc(100vh - 55px)"
    >
      <div class="container">
        <h2 class="text-center">Users</h2>
        <p class="text-center">
          Total of <strong>{{ total }}</strong> user accounts.
        </p>

        <div class="row justify-content-md-center">
          <div
            class="col-md-auto btn-group"
            role="group"
            style="padding-bottom: 20px"
          >
            <button
              type="button"
              class="btn btn-success"
              data-toggle="modal"
              data-target="#createUser"
            >
              Create User
            </button>
            <button type="button" class="btn btn-secondary" @click="updatePage">
              Refresh
            </button>
          </div>
        </div>

        <div class="row justify-content-md-center" style="padding-bottom: 10px">
          <div class="col-md-2 text-right">
            <span>Limit</span>
          </div>
          <div class="col-md-2">
            <select
              v-model="limit"
              class="form-control form-control-sm text-inline"
            >
              <option>50</option>
              <option>100</option>
              <option>500</option>
              <option>1000</option>
            </select>
          </div>
        </div>

        <div>
          <table class="table table-hover table-sm">
            <thead class="remove-top-border">
              <tr>
                <th scope="col">Username</th>
                <th scope="col">Name</th>
                <th scope="col">Admin</th>
                <!-- <th class="text-center" scope="col">Edit</th> -->
                <th class="text-center" scope="col" @click="deleteUser(user)">
                  Delete
                </th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="(user, index) in users" :key="index">
                <td>{{ user.username }}</td>
                <td>{{ user.name }}</td>
                <td>
                  <i v-if="user.is_admin" class="fa fa-circle text-center" />
                  <i v-else class="fa fa-circle-thin text-center" />
                </td>
                <!-- <td><i class="fa fa-pencil text-center edit-icon" @click="editUser(user)" /></td> -->
                <td>
                  <i
                    class="fa fa-remove text-center delete-icon"
                    @click="deleteUser(user)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="modal fade" tabindex="-1" role="dialog" id="createUser">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Create a User</h5>
            <button
              type="button"
              class="close"
              data-dismiss="modal"
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
          <div class="modal-body">
            <form>
              <div
                class="form-group"
                :class="{ 'was-validated': create.username.length !== 0 }"
              >
                <label>Username</label>
                <input
                  v-model="create.username"
                  class="form-control"
                  placeholder="Username"
                  required
                />
              </div>
              <div
                class="form-group"
                :class="{ 'was-validated': create.password.length !== 0 }"
              >
                <label>Password</label>
                <input
                  v-model="create.password"
                  class="form-control"
                  placeholder="Password"
                  required
                />
              </div>
              <div
                class="form-group"
                :class="{ 'was-validated': create.name.length !== 0 }"
              >
                <label>Name</label>
                <input
                  v-model="create.name"
                  class="form-control"
                  placeholder="Name"
                  required
                />
              </div>
              <div class="form-check">
                <input
                  v-model="create.isAdmin"
                  type="checkbox"
                  class="form-check-input"
                />
                <label class="form-check-label">Admin</label>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="submit" class="btn btn-primary" @click="createUser">
              Create User
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-dismiss="modal"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AdminPanel from "@/models/admin";
import toastrs from "@/mixins/toastrs";
import { mapMutations } from "vuex";

export default {
  name: "AdminPanel",
  mixins: [toastrs],
  data() {
    return {
      users: [],
      limit: 50,
      total: 0,
      create: {
        name: "",
        username: "",
        isAdmin: false,
        password: ""
      }
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    updatePage() {
      let process = "Loading users";
      this.addProcess(process);

      AdminPanel.getUsers(this.limit)
        .then(response => {
          this.users = response.data.users;
          this.total = response.data.total;
        })
        .finally(() => this.removeProcess(process));
    },
    createUser(event) {
      event.preventDefault();

      AdminPanel.createUser(this.create)
        .then(this.updatePage)
        .catch(error => {
          this.axiosReqestError("Create User", error.response.data.message);
        });
    },
    editUser() {},
    deleteUser(user) {
      let yes = confirm(
        "Are you sure you want to delete " +
          user.username +
          ". This action cannot be undone."
      );
      if (!yes) return;

      AdminPanel.deleteUser(user.username)
        .then(this.updatePage)
        .catch(error => {
          this.axiosReqestError("Create User", error.response.data.message);
        });
    }
  },
  watch: {
    limit: "updatePage"
  },
  created() {
    this.updatePage();
  }
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
