<template>
  <div class="card text-left">
  
    <div class="card-body title" @click="showLogs = !showLogs">
      
      {{ task.name }}

      <!--<span class="time text-muted">(Running for {{ time }})</span>-->
      
      <div style="float: right">
       
        <span v-show="errors > 0" class="badge badge-danger">
          {{ errors }} error<span v-show="errors > 1">s</span>
        </span>
        
        <span v-show="warnings > 0" class="badge badge-warning">
          {{ warnings }} warning<span v-show="warnings > 1">s</span>
        </span>

      </div>
    </div>
  
    <div v-show="showLogs" class="card-body">
      <div class="logs">
        <p
          class="log"
          :key="index"
          v-for="(line, index) in logs.slice().reverse()"
          :style="{ 'color': textColor(line) }"
        >{{ line }}</p>
      </div>
      <button class="btn btn-danger btn-block btn-sm delete" @click="deleteTask">
        Delete Task
      </button>
    </div>

    <div class="progress">
      <div
        class="progress-bar"
        :class="{ 'bg-success': task.progress >= 100 || task.completed }"
        :style="{ 'width': task.progress + '%' }"
      >
      </div>
    </div>

  </div>
</template>

<script>
import Tasks from "@/models/tasks";

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
      logs: ["Loading logs"],
      showLogs: false,
      onlyErrors: false,
      onlyWarnings: false
    };
  },
  sockets: {
    taskLogs(data) {
      if (data.id !== this.task.id) return;
    },
    taskProgress(data) {
      if (data.id !== this.task.id) return;

      this.task.progress = data.progress;
    }
  },
  methods: {
    textColor(text) {
      if (text.includes("[ERROR]")) return "red";
      if (text.includes("[WARNING]")) return "yellow";
      return "whtie";
    },
    deleteTask() {
      Tasks.delete(this.task.id).finally(() => {
        this.$parent.$parent.updatePage();
      });
    },
    getLogs() {
      Tasks.getLogs(this.task.id).then(response => {
        this.logs = response.data.logs;
      });
    }
  },
  watch: {
    showLogs: "getLogs"
  },
  computed: {
    warnings() {
      let warnings = this.task.warnings;
      if (warnings == null) return 0;
      return warnings;
    },
    errors() {
      let errors = this.task.errors;
      if (errors == null) return 0;
      return errors;
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

  -webkit-box-shadow: inset 0px 0px 30px 2px rgba(0, 0, 0, 0.2);
  -moz-box-shadow: inset 0px 0px 30px 2px rgba(0, 0, 0, 0.2);
  box-shadow: inset 0px 0px 30px 2px rgba(0, 0, 0, 0.2);
  font-family: "Courier New", Courier, monospace;
}

.log {
  color: white;
  font-size: 13px;
  margin: 0;
  padding: 0 5px;
}

.delete {
  margin: 2px 0;
}

.title {
  padding: 3px 15px;
  cursor: pointer;
}
</style>
