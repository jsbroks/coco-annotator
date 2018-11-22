<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="album py-5 bg-light" style="overflow: auto; height: calc(100vh - 55px)">
      <div class="container">
        <h2 class="text-center">Dataset of {{ dataset.name }}</h2>
        <p class="text-center">
          Total of <strong>{{ imageCount }}</strong> images displayed on <strong>{{ pages }}</strong> pages.
        </p>
        <!--
            <div v-if="subdirectories.length > 0" class="text-center">
                <h5>Subdirectories</h5>
                <button v-for="subdirectory in subdirectories"
                        class="btn badge badge-pill badge-primary category-badge"
                        style="margin: 2px" @click="folders.push(subdirectory)">{{ subdirectory }}
                </button>
            </div>
            -->
        <p class="text-center" v-if="images.length < 1">You need to upload some images!</p>
        <div v-else>
          <!--
                <ol class="breadcrumb">
                    <li class="breadcrumb-item" aria-current="page"></li>
                    <li class="breadcrumb-item" aria-current="page">{{ dataset.name }}</li>
                    <li v-for="folder in folders" class="breadcrumb-item" aria-current="page">{{ folder }}</li>
                </ol>
                -->

          <hr>
          <Pagination :pages="pages" @pagechange="updatePage" />
          <div class="row">
            <ImageCard v-for="image in images" :key="image.id" :image="image" />
          </div>
          <hr>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

import toastrs from "@/mixins/toastrs";

import ImageCard from "@/components/cards/ImageCard";
import Pagination from "@/components/Pagination";

export default {
  name: "Dataset",
  components: { ImageCard, Pagination },
  mixins: [toastrs],
  props: {
    identifier: {
      type: [Number, String],
      required: true
    }
  },
  data() {
    return {
      pages: 1,
      limit: 52,
      imageCount: 0,
      images: [],
      folders: [],
      dataset: {
        id: 0
      },
      subdirectories: [],
      status: {
        data: { state: true, message: "Loading data" }
      }
    };
  },
  methods: {
    updatePage(page) {
      this.status.data.state = false;
      axios
        .get("/api/dataset/" + this.dataset.id + "/data", {
          params: {
            page: page,
            limit: this.limit
          }
        })
        .then(response => {
          this.images = response.data.images;
          this.dataset = response.data.dataset;

          this.imageCount = response.data.pagination.total;
          this.pages = response.data.pagination.pages;

          this.subdirectories = response.data.subdirectories;

          this.status.data.state = true;
        })
        .catch(error => {
          this.axiosReqestError("Loading Dataset", error.response.data.message);
        });
    }
  },
  beforeRouteUpdate() {
    this.dataset.id = parseInt(this.identifier);
    this.updatePage();
  },
  created() {
    this.dataset.id = parseInt(this.identifier);
    this.updatePage();
  }
};
</script>
