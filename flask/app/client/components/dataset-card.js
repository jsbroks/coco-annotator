define(['Vue', 'axios'], function (Vue, axios) {

    Vue.component('dataset-card', {
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
        data: function () {
            return {
                    selectedCategories: []
            }
        },
        template: `
            <div class="col-md-3">
            
                <div class="card mb-4 box-shadow">
                    <img @click="onImageClick" :src="imageUrl" class="card-img-top"
                        style="width: 100%; display: block;">
                    
                    <div class="card-body">
                        <span class="d-inline-block text-truncate" style="max-width: 85%;">
                            <strong class="card-title">{{ dataset.name}}</strong>
                        </span>
                        <i class="card-text fa fa-ellipsis-v fa-x icon-more" :id="'dropdownDataset' + dataset.id"
                            data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" aria-hidden="true"></i>
                            
                        <div>
                            <p v-if="dataset.numberImages > 0">
                                {{ dataset.numberAnnotated}} of {{dataset.numberImages}} images annotated.
                            </p>
                            <p v-else>No images in dataset.</p>
                        
                            <span v-for="category in listCategories"
                                class="badge badge-pill badge-primary category-badge"
                                :style="{ 'background-color': category.color}">{{ category.name }}</span>
                                
                        </div>
                        
                        <div class="dropdown-menu" :aria-labelledby="'dropdownDataset' + dataset.id">
                            <a class="dropdown-item" data-toggle="modal" :data-target="'#datasetEdit' + dataset.id"
                                @click="selectedCategories = dataset.categories">
                                Edit
                            </a>
                            <a class="dropdown-item" @click="onDeleteClick">Delete</a>
                            <a class="dropdown-item" @click="onCocoDownloadClick">Download COCO</a>
                        </div>
                    </div>
                </div>
                
                <div class="modal fade" tabindex="-1" role="dialog" :id="'datasetEdit' + dataset.id">
                    <div class="modal-dialog" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">{{ dataset.name }}</h5>
                                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                    <span aria-hidden="true">&times;</span>
                                </button>
                            </div>
                            <div class="modal-body">
                                <form>
 
                                    <div class="form-group">
                                        <label>
                                            Categories <i v-if="categories.length == 0">(No categories found)</i>
                                        </label>
                                        <select v-model="selectedCategories" multiple class="form-control">
                                            <option v-for="category in categories" :key="category.id" :value="category.id">
                                                {{ category.name }}
                                            </option>
                                        </select>
                                    </div>
                                </form>  
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-success" @click="onSave" data-dismiss="modal">Save</button>
                                <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                 </div>
                 
            </div>
            
        `,
        computed: {
            imageUrl: function () {
                return this.dataset.numberImages > 0 ?
                    '/api/image/' + this.dataset.first_image_id : '/client/img/no-image.png'
            },
            listCategories: function () {
                let list = [];
                if (!this.dataset.hasOwnProperty('categories')) return [];
                if (this.dataset.categories.length === 0) return [];

                this.dataset.categories.forEach(category => {

                    let elements = this.categories.filter(element => {
                        if (element.id === category) {
                            return element;
                        }
                    });

                    if (elements.length === 1) {
                        list.push(elements[0])
                    }
                });

                return list;
            }
        },
        methods: {
            onImageClick: function () {
                if (this.dataset.numberImages > 0) {
                    document.location.pathname = '/images/' + this.dataset.id;
                }
            },
            onCocoDownloadClick: function () {
                this.$parent.status.downloading.message = "Generating coco for " + this.dataset.name;
                this.$parent.status.downloading.state = false;
                axios.get("/api/dataset/" + this.dataset.id + "/coco").then(reponse => {
                    let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(reponse.data));
                    this.downloadURI(dataStr, this.dataset.name + ".json");
                    this.$parent.status.downloading.state = true;
                });
            },
            onDeleteClick: function () {
                axios.delete('/api/dataset/' + this.dataset.id)
                    .then(repsonse => {
                        this.$parent.updatePage()
                    });
            },
            onSave: function () {
                this.dataset.categories = this.selectedCategories;
                console.log(axios.baseURL);
                axios.post('/api/dataset/' + this.dataset.id, {
                    'categories': this.selectedCategories
                }).then(response => {

                });
            },

            /**
             * Utilities
             */

            downloadURI: function (uri, exportName) {
                let link = document.createElement("a");
                link.href = uri;
                link.download = exportName;
                document.body.appendChild(link);
                link.click();
                link.remove();
            },
        }
    });
});
