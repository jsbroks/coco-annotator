<template>
  <div>
    <i 
      v-show="previousimage != null" 
      class="fa fa-arrow-left image-arrows" 
      style="float:left"
      @click="routePreviousImage"
    />

    <i 
      v-show="nextimage != null" 
      class="fa fa-arrow-right image-arrows" 
      style="float:right"
      @click="routeNextImage"
    />

    <h6 
      class="text-center" 
      style="color: white;"
    >
      <span 
        class="d-inline-block text-truncate" 
        style="max-width: 73%;"
      >{{ filename }}</span>
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
    routePreviousImage() {
      this.route(this.previousimage);
    },
    routeNextImage() {
      this.route(this.nextimage);
    },
    route(fileId) {
      this.$router.push({ name: "annotate", params: { fileId } });
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
