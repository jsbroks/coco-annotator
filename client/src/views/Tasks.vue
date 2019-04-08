<template>
  <div>
    <div style="padding-top: 55px" />
    <div
      class="album py-5 bg-light shadow-sm"
      style="overflow: auto; height: calc(100vh - 55px)"
    >
      <div class="container">
        <h2 class="text-center">Tasks</h2>
        <p class="text-center"><b>{{ total }}</b> tasks are running</p>
      
        <hr>

        <TaskGroup
          v-for="group in groups"
          :key="group"
          :name="group"
          :tasks="groupping[group]"
        />

      </div>
    </div>
  </div>
</template>

<script>
import toastrs from "@/mixins/toastrs";
import TaskGroup from "@/components/tasks/TaskGroup";
import Tasks from "@/models/tasks";

import { mapMutations } from "vuex";

export default {
  name: "Tasks",
  components: { TaskGroup },
  mixins: [toastrs],
  data() {
    return {
      total: 0,
      tasks: []
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    updatePage() {
      let process = "Loading tasks";
      this.addProcess(process);
      Tasks.all()
        .then(response => {
          this.tasks = response.data;
          if (this.taskToShow != null) {
            this.showTask(this.taskToShow);
          }
        })
        .finally(() => this.removeProcess(process));
    },
    showTask(taskId) {
      if (taskId == null) return;

      let task = this.tasks.find(t => t.id == taskId);
      if (task == null) return;
      task.show = true;
    }
  },
  watch: {
    taskToShow: "showTask"
  },
  computed: {
    taskToShow() {
      let taskId = this.$route.query.id;
      if (taskId == null) return null;

      return parseInt(taskId);
    },
    user() {
      return this.$store.state.user.user;
    },
    groups() {
      return Object.keys(this.groupping);
    },
    groupping() {
      let groupping = {};

      this.tasks.forEach(task => {
        if (task.hasOwnProperty("group")) {
          let group = task.group;

          if (!groupping.hasOwnProperty(group)) groupping[group] = [];

          groupping[group].push(task);
        }
      });

      return groupping;
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
