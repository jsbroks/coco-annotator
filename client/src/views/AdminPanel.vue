<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="album py-5 bg-light" style="overflow: auto; height: calc(100vh - 55px)">
      <div class="container">
        <h2 class="text-center">Users</h2>
        <p class="text-center">
          Total of <strong>{{ total }}</strong> user accounts.
        </p>

        <div class="row justify-content-md-center">
          <div class="col-md-auto btn-group" role="group" style="padding-bottom: 20px">
            <button type="button" class="btn btn-success disabled">Create User</button>
            <button type="button" class="btn btn-secondary" @click="updatePage">Refresh</button>
          </div>
        </div>

        <div class="row justify-content-md-center" style="padding-bottom: 10px">
          <div class="col-md-2 text-right">
            <span>Limit</span>
          </div>
          <div class="col-md-2">
            <select v-model="limit" class="form-control form-control-sm text-inline">
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
                <th class="text-center" scope="col">Delete</th>
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
                <td><i class="fa fa-remove text-center delete-icon" @click="deleteUser(user)" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

import { mapMutations } from "vuex";

export default {
  name: "AdminPanel",
  data() {
    return {
      users: [],
      limit: 50,
      total: 0
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    updatePage() {
      let process = "Loading users";
      this.addProcess(process);

      axios.get("/api/admin/users?limit=" + this.limit).then(response => {
        this.users = response.data.users;
        this.total = response.data.total;
        this.removeProcess(process);
      });
    },
    editUser(user) {},
    deleteUser(user) {}
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
