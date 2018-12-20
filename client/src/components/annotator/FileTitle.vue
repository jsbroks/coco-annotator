<template>
  <div>
    <i v-show="previousimage != null" class="fa fa-arrow-left image-arrows" style="float:left" @click="route(previousimage)" />
    
    <span v-show="previousimage != null" class="icon-stack" style="float:left" @click="route(previousimage, true)">
      <i  class="fa fa-clone" />
      <i  class="fa fa-long-arrow-left arrow" />
    </span>

    <i v-show="nextimage != null" class="fa fa-arrow-right image-arrows" style="float:right" @click="route(nextimage)" />
    <span v-show="nextimage != null" class="icon-stack" style="float:right" @click="route(nextimage, true)">
      <i  class="fa fa-clone" />
      <i  class="fa fa-long-arrow-right arrow" />
    </span>
    
    <h6 class="text-center" style="color: white;">
      <span class="d-inline-block text-truncate" style="max-width: 73%;">{{ filename }}</span>
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
    route(identifier, propagate) {
      this.$parent.save(() => {
        this.$router.push({
          name: "annotate",
          params: { identifier }
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
.icon-stack {
  position: relative;
  color: white;
}
.icon-stack .arrow {
  bottom: 0;
  margin-bottom: -7px;
  position: absolute;
  color: white;
  left: 0;
  width: 100%;
}
</style>
