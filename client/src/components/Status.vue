<template>
  <div class="form-inline my-2 my-lg-0" style="margin-right: 10px">
    <div
      class="my-sm-0 btn-sm disabled"
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
        return "Multiple tasks running ...";
      }
      if (this.process.length === 1) {
        return this.process[0];
      }

      if (this.lastProcess === "") {
        return "Done";
      }

      return (
        "Done " +
        this.lastProcess.charAt(0).toLowerCase() +
        this.lastProcess.slice(1)
      );
    },
    allLoaded() {
      return this.process.length === 0;
    }
  },
  watch: {
    process() {
      if (this.process.length === 1) {
        this.lastProcess = this.process[0];
      }
    }
  }
};
</script>

<style scoped>
.status-icon {
  margin: 3px 5px 0 0;
  float: left;
}
</style>
