<template>
  <div class="col-sm-6 col-md-4 col-xl-3 col-xxl-2">
    <div
      class="card mb-4 shadow-sm"
      :class="{'border': annotated, 'border-danger': annotated}"
      @mouseover="hover = true"
      @mouseleave="hover = false"
    >
      <div @click="openAnnotator">
        <v-lazy-image
          :src="imageUrl"
          :src-placeholder="loaderUrl"
          class="card-img-top"
          @error="imageError = true"
          style="width: 100%; display: block"
          :style="{'opacity': annotated ? 0.3 : 1}"
        />
      </div>

      <b v-if="annotated" class="overlay-text text-center">
        {{ $t('imageCard.beingAnnotated', { users: image.annotating.join(', ') }) }}
      </b>

      <div class="card-body" style="width: 100%" :style="{'opacity': annotated ? 0.3 : 1}">
        <div class="row" style="width: 100%">
          <span
            :class="{ 'text-truncate': !hover }"
            style="width: 100%; float: left"
          >
            <strong class="card-title">
              {{ image.id }}. {{ image.file_name }}
            </strong>
          </span>

          <i
            class="card-text fa fa-ellipsis-v fa-x icon-more"
            :id="'dropdownImage' + image.id"
            data-bs-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
            aria-hidden="true"
          />

          <div
            class="dropdown-menu"
            :aria-labelledby="'dropdownImage' + image.id"
          >
            <button
              class="btn dropdown-item"
              @click="onDeleteClick"
            >
              {{ $t('imageCard.delete') }}
            </button>
            <button class="btn dropdown-item" @click="openAnnotator">
              {{ $t('imageCard.annotate') }}
            </button>
            <button
              class="btn dropdown-item"
              @click="onDownloadClick"
            >
              {{ $t('imageCard.downloadImageCoco') }}
            </button>
          </div>
        </div>

        <div class="row">
          <p v-show="image.num_annotations > 0">
            {{ $t('imageCard.annotations', { n: image.num_annotations }, image.num_annotations) }}
          </p>
          <p v-show="image.annotated == true && image.num_annotations < 0">{{ $t('imageCard.annotated') }}</p>
          <p v-show="image.annotated == false">{{ $t('imageCard.noAnnotations') }}</p>
        </div>

        <div class="d-flex flex-wrap align-items-center gap-1 small">
          <span class="badge" :class="statusClass(image.status || 'unlabeled')" :title="image.review_note || ''">
            {{ $t('review.status.' + (image.status || 'unlabeled')) }}
          </span>
          <span v-if="image.ai" class="badge ai-badge" :title="$t('imageCard.aiHint')">
            <i class="fa fa-magic" /> AI
          </span>
          <span
            v-if="image.image_class != null && categoryMap[image.image_class]"
            class="badge"
            :style="{
              backgroundColor: categoryMap[image.image_class].color || 'var(--bs-primary)',
              color: textColorFor(categoryMap[image.image_class].color)
            }"
            :title="$t('imageClass.title')"
          >
            {{ categoryMap[image.image_class].name }}
          </span>
          <span v-if="image.assignee" class="text-muted text-truncate" :title="$t('review.assignee')">
            <i class="fa fa-user-o" /> {{ image.assignee }}
          </span>
        </div>

        <div class="row">
          <!--<span
            v-for="(category, index) in image.categories"
            :key="index"
            class="badge rounded-pill text-white category-badge"
            :style="{ 'background-color': category.color || 'var(--bs-primary)' }"
          >
            {{ category.name }}
          </span>-->
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import loaderImg from "@/assets/loader.gif";
import notFoundImageImg from "@/assets/404-image.png";
import axios from "axios";
import { statusClass } from "@/components/annotator/ReviewBar.vue";
import { textColorFor } from "@/libs/colors";

export default {
  name: "ImageCard",
  props: {
    image: {
      type: Object,
      required: true
    },
    /** { [category id]: { name, color } } for the whole-image class badge */
    categoryMap: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      hover: false,
      showAnnotations: true,
      loaderUrl: loaderImg,
      imageError: false
    };
  },
  methods: {
    statusClass,
    textColorFor,
    downloadURI(uri, exportName) {
      let link = document.createElement("a");
      link.href = uri;
      link.download = exportName;
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
    openAnnotator() {
      this.$router.push({
        name: "annotate",
        params: { identifier: this.image.id }
      });
    },
    onDownloadClick() {
      this.downloadURI(
        "/api/image/" + this.image.id + "?asAttachment=true",
        this.image.file_name
      );

      axios.get("/api/image/" + this.image.id + "/coco").then(reponse => {
        let dataStr =
          "data:text/json;charset=utf-8," +
          encodeURIComponent(JSON.stringify(reponse.data));
        this.downloadURI(
          dataStr,
          this.image.file_name.replace(/\.[^/.]+$/, "") + ".json"
        );
      });
    },
    onDeleteClick() {
      axios.delete("/api/image/" + this.image.id).then(() => {
        this.$parent.updatePage();
      });
    }
  },
  computed: {
    imageUrl() {
      // the file is missing on the server (deleted or moved on disk)
      if (this.imageError) return notFoundImageImg;
      let d = new Date();
      if (this.showAnnotations) {
        return `/api/image/${
          this.image.id
        }?width=250&thumbnail=true&dummy=${d.getTime()}`;
      } else {
        return "/api/image/" + this.image.id + "?width=250";
      }
    },
    annotated() {
      if (!this.image.annotating) return 0;
      return this.image.annotating.length > 0;
    }
  }
};
</script>

<style scoped>
.card-img-overlay {
  padding: 0;
}

.overlay-text {
  position: absolute;
  padding: 10px;
  top: 30px;
  width: 100%;
}

.card-body {
  margin: 5px 5px 0 5px;
  padding: 10px 20px;
}

p {
  margin: 0;
  padding: 0 0 3px 0;
}

.list-group-item {
  height: 21px;
  font-size: 13px;
  padding: 2px;
  background-color: #4b5162;
}
.icon-more {
  position: absolute;
  right: 5px;
  padding: 3px 10px;
  float: right;
  color: black;
}
.ai-badge {
  background: #ede7fb;
  color: #6a3fc4;
}
.category-badge {
  float: left;
  margin: 0 2px 5px 0;
}
</style>
