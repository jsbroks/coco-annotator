<template>
  <div class="d-flex align-items-center my-2 my-lg-0" style="margin-right: 10px">
    <div
      class="btn my-sm-0 btn-sm status-button"
      :class="buttonType"
      style="border: none"
    >
      <i
        v-if="allLoaded"
        class="fa fa-check fa-x status-icon"
        style="float:left"
      >
      </i>
      <i v-else class="fa fa-spinner fa-pulse fa-x fa-fw status-icon"></i>
      {{ message }}
    </div>
  </div>
</template>

<script>
import { processLabel } from "@/i18n";
export default {
  name: "Status",
  data() {
    return {
      lastProcess: ""
    };
  },
  computed: {
    buttonType() {
      if (this.allLoaded) {
        return "btn-outline-success";
      }
      return "btn-outline-danger";
    },
    process() {
      return this.$store.state.process;
    },
    message() {
      if (this.process.length > 1) {
        return this.$t("status.multiple");
      }
      if (this.process.length === 1) {
        return this.$t("status.running", { process: processLabel(this.process[0]) });
      }

      if (this.lastProcess === "") {
        return this.$t("status.done");
      }

      let label = processLabel(this.lastProcess);
      // "Done loading datasets" (English keeps the original lower-casing)
      return this.$t("status.doneWith", { process: label.charAt(0).toLowerCase() + label.slice(1) });
    },
    allLoaded() {
      return this.process.length === 0;
    }
  },
  watch: {
    process: {
      deep: true,
      handler() {
        if (this.process.length === 1) {
          this.lastProcess = this.process[0];
        }
      }
    }
  }
};
</script>

<style scoped>
.status-button {
  cursor: default;
  pointer-events: none;
}

.status-icon {
  margin: 3px 5px 0 0;
  float: left;
}
</style>
