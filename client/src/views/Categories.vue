<template>
  <div>
    <div style="padding-top: 55px" />
    <div
      class="album py-5 bg-light"
      style="overflow: auto; height: calc(100vh - 55px)"
    >
      <div class="container">
        <h2 class="text-center">
          Categories
          <i
            class="fa fa-question-circle help-icon"
            data-toggle="modal"
            data-target="#helpCategories"
            aria-hidden="true"
          />
        </h2>

        <p class="text-center">
          Loaded <strong>{{ categoryCount }}</strong> categories.
        </p>

        <div class="row justify-content-md-center">
          <div
            class="col-md-auto btn-group"
            role="group"
            style="padding-bottom: 20px"
          >
            <button
              type="button"
              class="btn btn-success"
              data-toggle="modal"
              data-target="#createCategories"
            >
              Create
            </button>
            <button type="button" class="btn btn-secondary" @click="updatePage">
              Refresh
            </button>
          </div>
        </div>

        <hr />

        <p v-if="categories.length < 1" class="text-center">
          You need to create a category!
        </p>
        <div v-else>
          <Pagination :pages="pages" @pagechange="updatePage" />

          <div class="row">
            <CategoryCard
              v-for="category in categories"
              :key="category.id"
              :category="category"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" tabindex="-1" role="dialog" id="createCategories">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Creating a Category</h5>
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
                <label>Category Name</label>
                <input
                  v-model="createName"
                  class="form-control"
                  placeholder="Category name"
                />
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-primary"
              @click="createCategory"
            >
              Create Category
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

    <div class="modal fade" tabindex="-1" role="dialog" id="helpCategories">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Categories</h5>
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
            More information can be found in the
            <a href="https://github.com/jsbroks/coco-annotator/wiki/Usage#creating-categories">
              getting started section
            </a>.
            <hr />
            <h6>What is a category?</h6>

            <hr />
            <h6>How do I create one?</h6>
            Click on the "Create" button found on this webpage. You must
            provided a name for the category.
          </div>
          <div class="modal-footer">
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
import toastrs from "@/mixins/toastrs";

import Category from "@/models/categories";
import CategoryCard from "@/components/cards/CategoryCard";
import Pagination from "@/components/Pagination";

import { mapMutations } from "vuex";

export default {
  name: "Categories",
  components: { CategoryCard, Pagination },
  mixins: [toastrs],
  data() {
    return {
      categoryCount: 0,
      pages: 1,
      page: 1,
      limit: 50,
      range: 11,
      createName: "",
      categories: [],
      status: {
        data: { state: true, message: "Loading categories" }
      }
    };
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    updatePage(page) {
      let process = "Loading categories";
      this.addProcess(process);

      page = page || this.page;
      this.page = page;

      Category.allData({
        page: page,
        limit: this.limit
      })
        .then(response => {
          this.categories = response.data.categories;
          this.page = response.data.pagination.page;
          this.pages = response.data.pagination.pages;
          this.categoryCount = response.data.pagination.total;
        })
        .finally(() => this.removeProcess(process));
    },
    createCategory() {
      if (this.createName.length < 1) return;

      Category.create({
        name: this.createName
      })
        .then(() => {
          this.createName = "";
          this.updatePage();
        })
        .catch(error => {
          this.axiosReqestError(
            "Creating Category",
            error.response.data.message
          );
        });
    },
    previousPage() {
      this.page -= 1;
      if (this.page < 1) {
        this.page = 1;
      }
    },
    nextPage: function() {
      this.page += 1;
      if (this.page > this.pages) {
        this.page = this.pages;
      }
    }
  },
  created() {
    this.updatePage();
  }
};
</script>

<style scoped>
.card-img-overlay {
  padding: 0 10px 0 0;
}

.icon-more {
  width: 10%;
  margin: 3px 0;
  padding: 0;
  float: right;
  color: black;
}

.help-icon {
  color: darkblue;
  font-size: 20px;
  display: inline;
}
</style>
