<template>
  <div>
    <div style="padding-top: 55px" />
    <div
      class="album py-5 bg-light "
      style="overflow: auto; height: calc(100vh - 55px)"
    >
      <div class="container">
        <h2 class="text-center">Tasks</h2>
        <p class="text-center"><b>{{ total }}</b> tasks are running</p>
      
        <hr>

        <TaskGroup v-for="group in groups" :key="group" :name="group" :tasks="tasks[group]" />
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import toastrs from "@/mixins/toastrs";
import TaskGroup from "@/components/tasks/TaskGroup";

import { mapMutations } from "vuex";

export default {
  name: "Tasks",
  components: { TaskGroup },
  mixins: [toastrs],
  data() {
    return {
      total: 0,
      tasks: {
        Import: [
          {
            id: 1203,
            progress: 0,
            name: "Importing test 1",
            errors: ["Could not import Image 1"],
            logs: ["Starting Task", "Importing images"]
          },
          {
            id: 1203,
            progress: 10,
            name: "Importing test 1",
            errors: ["Could not import Image 1"],
            logs: ["Starting Task", "Importing images"]
          },
          {
            id: 1203,
            progress: 20,
            name: "Importing test 1",
            errors: ["Could not import Image 1"],
            logs: [
              "Starting Task",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images",
              "Importing images"
            ]
          },
          {
            id: 1203,
            name: "Importing test 1",
            errors: ["Could not import Image 1"],
            logs: ["Starting Task", "Importing images"]
          }
        ],
        Export: [
          {
            id: 1203,
            name: "Exporting test 1",
            errors: ["Could not import Image 1"],
            logs: ["Starting Task", "Importing images"]
          }
        ],
        Scan: [
          {
            id: 1203,
            name: "Scaning test 1",
            errors: ["Could not import Image 1"],
            logs: ["Starting Task", "Importing images"]
          }
        ]
      }
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    updatePage() {}
  },
  watch: {
    user() {
      this.updatePage();
    }
  },
  computed: {
    user() {
      return this.$store.state.user.user;
    },
    groups() {
      return Object.keys(this.tasks);
    }
  },
  created() {
    this.updatePage();
  }
};
</script>

<style scoped>
.help-icon {
  color: darkblue;
  font-size: 20px;
  display: inline;
}
</style>
