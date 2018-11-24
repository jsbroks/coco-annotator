<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="album py-5 bg-light" style="overflow: auto; height: calc(100vh - 55px)">
      <div class="container">
        <h2 class="text-center">Undo</h2>
        <p class="text-center">
          Total of <strong>{{ undos.length }}</strong> items can be undone.
        </p>

        <div class="row justify-content-md-center">
          <div class="col-md-auto btn-group" role="group" style="padding-bottom: 20px">
            <button type="button" class="btn btn-success disabled">Undo All</button>
            <button type="button" class="btn btn-danger disabled">Delete All</button>
            <button type="button" class="btn btn-secondary" @click="updatePage">Refresh</button>
          </div>
        </div>
        <p class="text-center" v-if="undos.length < 1">Nothing to undone!</p>
        <div v-else>
          <table class="table table-hover table-sm">
            <thead class="remove-top-border">
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Instance Type</th>
                <th scope="col">ID</th>
                <th scope="col">Name</th>
                <th class="text-center" scope="col">Rollback</th>
                <th class="text-center" scope="col">Delete</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="(undo, index) in undos" :key="index">
                <td>{{ undo.ago }} ago</td>
                <td>{{ undo.instance }}</td>
                <td>{{ undo.id }}</td>
                <td>{{ undo.name }}</td>
                <td><i class="fa fa-undo text-center undo-icon" aria-hidden="true" @click="undoModel(undo.id, undo.instance)" /></td>
                <td><i class="fa fa-remove text-center delete-icon" aria-hidden="true" @click="deleteModel(undo.id, undo.instance)" /></td>
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

export default {
  name: "Undo",
  data() {
    return {
      undos: [],
      status: {
        data: { state: true, message: "Loading data" }
      }
    };
  },
  methods: {
    updatePage() {
      this.status.data.state = false;
      axios.get("/api/undo/list/").then(response => {
        this.undos = response.data;

        this.status.data.state = true;
      });
    },
    undoModel(id, instance) {
      axios.post("/api/undo/?id=" + id + "&instance=" + instance).then(() => {
        this.updatePage();
      });
    },
    deleteModel(id, instance) {
      axios.delete("/api/undo/?id=" + id + "&instance=" + instance).then(() => {
        this.updatePage();
      });
    }
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

.undo-icon:hover {
  color: green;
}

.delete-icon:hover {
  color: red;
}
</style>
