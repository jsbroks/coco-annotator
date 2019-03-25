<template>
  <div class="col-md-3">
    <div class="card mb-4 box-shadow" @click="onCardClick">
      <div class="card-body">
        <span
          class="d-inline-block text-truncate"
          style="max-width: 75%; float: left"
        >
          <i
            class="fa fa-circle color-icon"
            aria-hidden="true"
            :style="{ color: category.color }"
          />
          <strong class="card-title">{{ category.name }}</strong>
        </span>

        <i
          class="card-text fa fa-ellipsis-v fa-x icon-more"
          :id="'dropdownCategory' + category.id"
          data-toggle="dropdown"
          aria-haspopup="true"
          aria-expanded="false"
          aria-hidden="true"
        />

        <br />

        <div>
          <p v-if="category.numberAnnotations > 0">
            {{ category.numberAnnotations }} objects have been made with this
            category.
          </p>
          <p v-else>No annotations use this category</p>
        </div>

        <div
          class="dropdown-menu"
          :aria-labelledby="'dropdownCategory' + category.id"
        >
          <!--<a class="dropdown-item" @click="onEditClick">Edit</a>-->
          <a class="dropdown-item" @click="onDeleteClick">Delete</a>
          <!--<a class="dropdown-item" @click="onDownloadClick"
            >Download COCO & Images</a
          >-->
          <button
            class="dropdown-item"
            data-toggle="modal"
            :data-target="'#categoryEdit' + category.id"
          >
            Edit
          </button>
        </div>
      </div>

      <div
        v-show="$store.getters['user/loginEnabled']"
        class="card-footer text-muted"
      >
        Created by {{ category.creator }}
      </div>
    </div>

    <div class="modal fade" role="dialog" :id="'categoryEdit' + category.id">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Current Name: {{ category.name }}</h5>
            <button
              type="button"
              class="close"
              data-dismiss="modal"
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
          <div class="modal-body">
            <form>
              <div class="form-group">
                <label>Edit name: </label>
                <input type="text" 
                :value="category.name"
                @input="updatedCategoryName = $event.target.value">
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-success"
              @click="onUpdateClick"
              data-dismiss="modal"
            >
              Update
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-dismiss="modal"
            >
              Close
            </button>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<script>
import axios from "axios";
import toastrs from "@/mixins/toastrs";

export default {
  name: "CategoryCard",
  mixins: [toastrs],
  data() {
    return {
      updatedCategoryName: ""
    };
  },
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
    },
    onUpdateClick() {
      axios
        .put("/api/category/" + this.category.id, {
          name: this.updatedCategoryName
        })
        .then(() => {
          this.axiosReqestSuccess(
            "Updating Category",
            "Category name has been updated"
          );
          this.category.name = this.updatedCategoryName;
          this.$parent.updatePage();
        })
        .catch(error => {
          this.axiosReqestError(
            "Updating Category",
            error.response.data.message
          );
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
  margin: 0;
  padding-right: 10px;
}

.card-footer {
  padding: 2px;
  font-size: 11px;
}
</style>
