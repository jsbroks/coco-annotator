<template>
  <div class="col-md-3">
      
      <!-- Dataset Card -->
      <div class="card mb-4 box-shadow">
        <!-- Display Image -->
        <img 
          @click="onImageClick" 
          :src="imageUrl" 
          class="card-img-top"
          style="width: 100%; display: block;"
        >

        <!-- Card Body -->                    
        <div class="card-body">
          <span 
            class="d-inline-block text-truncate" 
            style="max-width: 85%; float: left"
          >
            <strong class="card-title">{{ dataset.name }}</strong>
          </span>
                    
          <i 
            class="card-text fa fa-ellipsis-v fa-x icon-more" 
            :id="'dropdownDataset' + dataset.id"
            data-toggle="dropdown" 
            aria-haspopup="true" 
            aria-expanded="false" 
            aria-hidden="true"
          />
          
          <br>

          <div style="float: left">
            <p v-if="dataset.numberImages > 0">
              {{ dataset.numberAnnotated }} of {{ dataset.numberImages }} images annotated.
            </p>
            <p v-else>No images in dataset.</p> 
            <span 
              v-for="(category, index) in listCategories"
              :key="index"
              class="badge badge-pill badge-primary category-badge"
              :style="{ 'background-color': category.color}"
            >{{ category.name }}</span>                              
          </div>
                        
          <div 
            class="dropdown-menu" 
            :aria-labelledby="'dropdownDataset' + dataset.id"
          >
            <a 
              class="dropdown-item" 
              data-toggle="modal" 
              :data-target="'#datasetEdit' + dataset.id"
              @click="selectedCategories = dataset.categories"
            >
              Edit
            </a>
            <a 
              class="dropdown-item" 
              @click="onDeleteClick"
            >Delete</a>
            <a 
              class="dropdown-item" 
              @click="onCocoDownloadClick"
            >Download COCO</a>
          </div>
        </div>
        
      </div>

      <!-- Edit Dataset -->          
      <div 
        class="modal fade" 
        tabindex="-1" 
        role="dialog" 
        :id="'datasetEdit' + dataset.id"
      >
        <div 
          class="modal-dialog" 
          role="document"
        >
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">{{ dataset.name }}</h5>
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
                  <label>
                    Categories <i v-if="categories.length == 0">(No categories found)</i>
                  </label>
                  <select 
                    v-model="selectedCategories" 
                    multiple 
                    class="form-control"
                  >
                    <option 
                      v-for="category in categories" 
                      :key="category.id" 
                      :value="category.id"
                    >
                      {{ category.name }}
                    </option>
                  </select>
                </div>
                                    
                <!--<metadata 
                  :metadata="defaultMetadata" 
                  title="Default Annotation Metadata"
                  key-name="Default Key" 
                  value-name="Default Value"
                  ref="defaultAnnotation"
                />-->
              </form>  
            </div>
            <div class="modal-footer">
              <button 
                type="button" 
                class="btn btn-success" 
                @click="onSave" 
                data-dismiss="modal"
              >Save</button>
              <button 
                type="button" 
                class="btn btn-secondary" 
                data-dismiss="modal"
              >Close</button>
            </div>
          </div>
        </div>
      </div>
                 
    </div>    
  </div>
</template>

<script>
export default {
  name: "DatasetCard",
  props: {
    dataset: {
      type: Object,
      required: true
    },
    categories: {
      type: Array,
      required: true
    }
  },
  data() {
    return {
      selectedCategories: [],
      defaultMetadata: this.dataset.default_annotation_metadata
    };
  },
  methods: {
    onImageClick() {},
    onCocoDownloadClick() {},
    onDeleteClick() {},
    onSave() {}
  },
  computed: {
    imageUrl() {
      return this.dataset.numberImages > 0
        ? "/api/image/" + this.dataset.first_image_id + "?width=250"
        : "https://picsum.photos/200/300/?random";
    },
    listCategories() {
      let list = [];
      if (!this.dataset.hasOwnProperty("categories")) return [];
      if (this.dataset.categories.length === 0) return [];

      this.dataset.categories.forEach(category => {
        let elements = this.categories.filter(element => {
          if (element.id === category) {
            return element;
          }
        });

        if (elements.length === 1) {
          list.push(elements[0]);
        }
      });

      return list;
    }
  }
};
</script>

<style scoped>
.card-img-overlay {
  padding: 0 10px 0 0;
}

.card-body {
  padding: 10px 10px 0 10px;
}

p {
  margin: 0;
  padding: 0 0 3px 0;
}

.category-badge {
  float: left;
  margin: 0 2px 5px 0;
}

.list-group-item {
  height: 21px;
  font-size: 13px;
  padding: 2px;
  background-color: #4b5162;
}
.icon-more {
    width: 10%;
    margin: 3px 0;
    padding: 0;
    float: right;
    color: black;
}

</style>
