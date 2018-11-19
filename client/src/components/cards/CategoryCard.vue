<template>
  <div class="col-md-3">
    <div class="card mb-4 box-shadow" @click="onCardClick">

      <div class="card-body">
        <span class="d-inline-block text-truncate" style="max-width: 75%; float: left">
          <i class="fa fa-circle color-icon" aria-hidden="true" :style="{ color: category.color }" />
          <strong class="card-title">{{ category.name }}</strong>
        </span>

        <i class="card-text fa fa-ellipsis-v fa-x icon-more" :id="'dropdownCategory' + category.id" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" aria-hidden="true" />

        <br>

        <div>
          <p v-if="category.numberAnnotations > 0">
            {{ category.numberAnnotations }} objects have been made with this category.
          </p>
          <p v-else>No annotations use this category</p>
        </div>

        <div class="dropdown-menu" :aria-labelledby="'dropdownCategory' + category.id">
          <a class="dropdown-item" @click="onEditClick">Edit</a>
          <a class="dropdown-item" @click="onDeleteClick">Delete</a>
          <a class="dropdown-item" @click="onDownloadClick">Download COCO & Images</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "CategoryCard",
  props: {
    category: {
      type: Object,
      required: true
    }
  },
  methods: {
    onEditClick() {},
    onCardClick() {},
    onDownloadClick() {},
    onDeleteClick() {
      axios.delete("/api/category/" + this.category.id).then(() => {
        this.$parent.updatePage();
      });
    }
  }
};
</script>

<style scoped>
.icon-more {
  width: 10%;
  margin: 3px 0;
  padding: 0;
  float: right;
  color: black;
}

.card-body {
  padding: 10px 10px 0 10px;
}

.color-icon {
  display: inline;
  width: 10%;
  margin: 0;
  padding-right: 10px;
}
</style>
