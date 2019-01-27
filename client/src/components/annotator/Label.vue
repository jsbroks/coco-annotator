<template>
  <div class="card" @click="click" v-show="show">
    <div class="card-header" :id="'heading' + category.id">
      <div :style="{ color: isSelected ? 'white' : 'gray' }">
        <div>
          <i v-if="isSelected" class="fa fa-check-square-o category-icon" />
          <i v-else class="fa fa-square-o category-icon" />
        </div>

        <span
          class="btn btn-link btn-sm collapsed category-text"
          style="color: inherit"
          aria-expanded="false"
        >
          {{ category.name }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "Label",
  model: {
    prop: "categoryIds",
    event: "update"
  },
  props: {
    category: {
      type: Object,
      required: true
    },
    categoryIds: {
      type: Array,
      required: true
    },
    search: {
      type: String,
      required: true
    }
  },
  data() {
    return {};
  },
  computed: {
    show() {
      let search = this.search.toLowerCase();
      if (search.length === 0) return true;
      return this.category.name.toLowerCase().includes(search);
    },
    isSelected() {
      return this.categoryIds.indexOf(this.category.id) > -1;
    }
  },
  methods: {
    click() {
      let copy = this.categoryIds.slice();
      if (!this.isSelected) {
        copy.push(this.category.id);
      } else {
        copy.splice(copy.indexOf(this.category.id), 1);
      }
      this.$emit("update", copy);
    }
  }
};
</script>

<style scoped>
.list-group-item {
  height: 22px;
  font-size: 13px;
  padding: 2px;
  background-color: #404552;
}

.category-icon {
  display: block;
  float: left;
  margin: 0;
  padding: 5px 10px 5px 10px;
}

.btn-link {
  margin: 0;
  padding: 0;
}
.annotation-icon {
  margin: 0;
  padding: 3px;
}

.card-header {
  display: block;
  margin: 0;
  padding: 0;
}

.card {
  background-color: #4b5162;
}
</style>
