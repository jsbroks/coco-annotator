<template>
  <div
    class="card text-left"
    :id="'task-' + this.task.id"
    :style="{ 'background-color': highlight ? 'lightgreen' : 'white'}"
  >
  
    <div class="card-body title" @click="showLogs = !showLogs">
      
      <span class="text-muted">{{ task.id }}.</span> {{ task.name }}

      <!--<span class="time text-muted">(Running for {{ time }})</span>-->
      
      <div style="float: right">
       
        <span v-show="errors > 0" class="badge badge-danger" @click.stop="onlyErrors = !onlyErrors">
          {{ errors }} error<span v-show="errors > 1">s</span>
        </span>
        
        <span v-show="warnings > 0" class="badge badge-warning" @click.stop="onlyWarnings = !onlyWarnings">
          {{ warnings }} warning<span v-show="warnings > 1">s</span>
        </span>

      </div>
    </div>
  
    <div v-show="showLogs" class="card-body">
      <div class="logs">
        <p
          class="log"
          :key="index"
          v-for="(line, index) in displayLogs.slice().reverse()"
          :style="{ 'color': textColor(line) }"
        >{{ line }}</p>
      </div>
      <button v-show="completed" class="btn btn-danger btn-block btn-sm delete" @click="deleteTask">
        Delete
      </button>
    </div>

    <div class="progress">
      <div
        class="progress-bar"
        :class="{ 'bg-success': completed }"
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
      highlight: false,
      onlyErrors: false,
      onlyWarnings: false
    };
  },
  sockets: {
    taskProgress(data) {
      if (data.id !== this.task.id) return;

      this.task.progress = data.progress;
      this.task.warnings = data.warnings;
      this.task.errors = data.errors;
    }
  },
  methods: {
    textColor(text) {
      if (text.includes("[ERROR]")) return "red";
      if (text.includes("[WARNING]")) return "yellow";
      return "white";
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
    showLogs: "getLogs",
    completed() {
      if (this.showLogs) {
        this.getLogs();
      }
    }
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
    },
    displayLogs() {
      let logs = this.logs;
      if (this.onlyErrors) return this.logs.filter(t => t.includes("[ERROR]"));
      if (this.onlyWarnings)
        return this.logs.filter(t => t.includes("[WARNING]"));

      return logs;
    },
    completed() {
      return this.task.completed || this.task.progress >= 100;
    }
  },
  mounted() {
    let show = this.task.show;
    if (show != null) {
      this.showLogs = show;

      if (show) {
        setTimeout(() => {
          this.highlight = true;
          this.$el.scrollIntoView({
            behavior: "smooth"
          });
          setTimeout(() => (this.highlight = false), 1000);
        }, 200);
      }
    }
  }
};
</script>

<style scoped>
.card {
  border: none;
  border-radius: 0;
  transition: background-color 500ms linear;
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
