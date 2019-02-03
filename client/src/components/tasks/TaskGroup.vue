<template>
  <div style="margin: 10px">
    <div class="card">

     <div class="card-header text-left" @click="showTasks = !showTasks">
        {{ name }}
      </div>

      <div v-show="showTasks" class="card-body">
        <Task v-for="task in tasks" :task="task" />
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
      showTasks: false
    };
  },
  computed: {}
};
</script>

<style scoped>
.card {
  margin: 0;
  padding: 0;
  cursor: pointer;
}

.card-header {
  background-color: white;
}

.card-body {
  padding: 0;
  margin: 0;
}
</style>
