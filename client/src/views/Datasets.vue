<template>
  <div>
    <div style="padding-top: 55px" />

    <div class="album py-5 bg-light" style="overflow: auto; height: calc(100vh - 55px)">
      <div class="container">

        <h2 class="text-center">
          Datasets
          <i class="fa fa-question-circle help-icon" data-toggle="modal" data-target="#helpDataset" aria-hidden="true" />
        </h2>

        <p class="text-center">
          Loaded <strong>{{ datasets.length }}</strong> datasets.</p>

        <div class="row justify-content-md-center">
          <div class="col-md-auto btn-group" role="group" style="padding-bottom: 20px">
            <button type="button" class="btn btn-success" data-toggle="modal" data-target="#createDataset">
              Create
            </button>
            <button type="button" class="btn btn-primary disabled">Import</button>
            <button type="button" class="btn btn-secondary" @click="updatePage">Refresh</button>
          </div>
        </div>

        <hr>
        <p v-if="datasets.length < 1" class="text-center">You need to create a dataset!</p>
        <div v-else style="background-color: gray">
          <Pagination :pages="pages" @pagechange="updatePage" />
          <div class="row bg-light">
            <DatasetCard v-for="dataset in datasets" :key="dataset.id" :dataset="dataset" :categories="categories" />
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" tabindex="-1" role="dialog" id="createDataset">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Creating a Dataset</h5>
            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
              <span aria-hidden="true">&times;</span>
            </button>
          </div>
          <div class="modal-body">
            <form>
              <div class="form-group" required>
                <label>Dataset Name</label>
                <input v-model="create.name" class="form-control" placeholder="Dataset name">
              </div>

              <div class="form-group">
                <label>Default Categories <i v-if="categories.length === 0">(No categories found)</i></label>
                <select v-model="create.categories" multiple class="form-control">
                  <option v-for="category in categories" :key="category.id" :value="category.id">
                    {{ category.name }}
                  </option>
                </select>
              </div>

              <div class="form-group" required>
                <label>Folder Directory</label>
                <input class="form-control" disabled :placeholder="create.directory">
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-primary" @click="createDataset">Create Dataset</button>
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" tabindex="-1" role="dialog" id="helpDataset">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Datasets</h5>
            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
              <span aria-hidden="true">&times;</span>
            </button>
          </div>

          <div class="modal-body">
            More information can be found in the <a href="/help">help section</a>.
            <hr>
            <h6>What is a dataset?</h6>
            A dataset is a collection of images. It provides default category options for all subsequent images.
            Each dataset has its own folder in the data/datasets directory.
            <hr>
            <h6>How do I create one?</h6>
            Click on the "Create" button found on this webpage. A dataset name must be provided.
            <hr>
            <h6>How do I add images?</h6>
            Once you have created a dataset you can add images by placing them in the create folder
            (well the server is running).
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import DatasetCard from "@/components/cards/DatasetCard";
import Pagination from "@/components/Pagination";

export default {
  name: "Datasets",
  components: { DatasetCard, Pagination },
  data() {
    return {
      pages: 1,
      limit: 4,
      page: 1,
      create: {
        name: "",
        categories: []
      },
      datasets: [],
      subdirectories: [],
      categories: []
    };
  },
  methods: {
    updatePage(page) {
      page = page||this.page
      this.page = page;

      axios.get("/api/dataset/data", {
        params: {
          limit: this.limit,
          page: page
        }
      }).then(response => {
        this.datasets = response.data.datasets;
        this.categories = response.data.categories;
        this.subdirectories = response.data.subdirectories;
        this.pages = response.data.pagination.pages;
        this.page = response.data.pagination.page;
      });
    },
    createDataset() {
      if (this.create.name.length < 1) return;
      let categories = [];

      for (let key in this.create.categories) {
        categories.push(this.create.categories[key]);
      }

      axios
        .post("/api/dataset/?name=" + this.create.name, {
          categories: categories
        })
        .then(() => {
          this.create.name = "";
          this.create.categories = [];
          this.updatePage();
        });
    }
  },
  created() {
    this.updatePage();
  }
};
</script>

<style scoped>
.help-icon {
  color: darkblue;
  font-size: 20px;
  display: inline;
}
</style>
