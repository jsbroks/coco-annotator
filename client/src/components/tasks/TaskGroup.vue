<template>
  <div style="margin: 10px">
    <div class="card">

      <div class="card-header text-left" @click="showTasks = !showTasks">
        {{ name }}

        <span style="float: right; color: light-gray">
          {{ runningTasks.length }} of {{ tasks.length }} task<span v-show="tasks.length != 1">s</span> running
        </span>
      </div>

      <div v-show="showTasks" class="card-body">
        <Task :key="index" v-for="(task, index) in tasks" :task="task" />
      </div>
    </div>
  </div>
</template>

<script>
import Task from "@/components/tasks/Task";

export default {
  name: "TaskGroup",
  components: { Task },
  props: {
    tasks: {
      type: Array,
      required: true
    },
    name: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      showTasks: true
    };
  },
  computed: {
    runningTasks() {
      return this.tasks.filter(t => t.progress < 100);
    }
  }
};
</script>

<style scoped>
.card {
  margin: 0;
  padding: 0;
  cursor: pointer;
}

.card-header {
  color: white;
  background-color: #383c4a;
}

.card-body {
  padding: 0;
  margin: 0;
}
</style>
