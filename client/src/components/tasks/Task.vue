<template>
  <div class="card text-left">
  
    <div class="card-body title" @click="showLogs = !showLogs">
      
      {{ task.name }}

      <span class="time text-muted">(Running for {{ time }})</span>
      <div style="float: right">
        <span v-show="task.errors.length > 0" class="badge badge-danger">
          {{ task.errors.length }} error<span v-show="errors.length > 1">s</span>
        </span>
        <span v-show="warnings.length > 0" class="badge badge-warning">
          {{ warnings.length }} warning<span v-show="warnings.length > 1">s</span>
        </span>
      </div>
    </div>
  
    <div v-show="showLogs" class="card-body">
      <div class="logs">
        <p class="log" :key="index" v-for="(line, index) in logs.slice().reverse()">{{ line }}</p>
      </div>
    </div>

    <div class="progress">
      <div class="progress-bar" :style="{ 'width': task.progress + '%' }"></div>
    </div>

  </div>
</template>

<script>
export default {
  name: "Task",
  props: {
    task: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      showLogs: false
    };
  },
  computed: {
    warnings() {
      let warnings = this.task.warnings;
      if (warnings == null) return [];
      return warnings;
    },
    errors() {
      let errors = this.task.errors;
      if (errors == null) return [];
      return errors;
    },
    logs() {
      let logs = this.task.logs;
      if (logs == null || this.task.logs.length == 0) return ["Logs are empty"];
      return logs;
    },
    time() {
      return "10 seconds";
    }
  }
};
</script>

<style scoped>
.card {
  border: none;
  border-radius: 0;
}
.progress {
  height: 3px;
}
.card-body {
  padding: 5px;
  margin: 0;
}

.badge {
  margin-left: 2px;
}

.time {
  font-size: 12px;
}

.logs {
  background-color: #4b5162;
  border-radius: 5px;
  max-height: 250px;
  overflow-y: auto;

  -webkit-box-shadow: inset 0px 0px 30px 2px rgba(0,0,0,0.2);
  -moz-box-shadow: inset 0px 0px 30px 2px rgba(0,0,0,0.2);
  box-shadow: inset 0px 0px 30px 2px rgba(0,0,0,0.2);
}

.log {
  color: white;
  font-size: 13px;
  margin: 0;
  padding: 0 5px;
}

.title {
  padding: 3px 15px;
  cursor: pointer;
}
</style>
