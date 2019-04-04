<template>
  <div>
    <i
      v-show="previousimage != null"
      class="fa fa-arrow-left image-arrows"
      style="float:left"
      @click="route(previousimage)"
    />
    <i
      v-show="nextimage != null"
      class="fa fa-arrow-right image-arrows"
      style="float:right"
      @click="route(nextimage)"
    />

    <h6 class="text-center" style="color: white;">
      <span class="d-inline-block text-truncate" style="max-width: 73%;">{{
        filename
      }}</span>
    </h6>
  </div>
</template>

<script>
export default {
  name: "FileTitle",
  props: {
    filename: {
      type: String,
      required: true
    },
    previousimage: {
      type: Number,
      default: null
    },
    nextimage: {
      type: Number,
      default: null
    }
  },
  methods: {
    /**
     * Navigates to image with provided ID
     *
     * @param {Number} identifer id of a file
     */
    route(identifier) {
      // Make sure we pop the latest session before annotations
      this.$parent.current.annotation = -1;

      this.$nextTick(() => {
        this.$parent.save(() => {
          this.$router.push({ name: "annotate", params: { identifier } });
        });
      });
    }
  }
};
</script>

<style scoped>
.image-arrows {
  color: white;
  position: relative;
  margin: 0 10px 15px 10px;
}
</style>
