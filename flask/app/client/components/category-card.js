define(['Vue', 'axios'], function (Vue, axios) {

    Vue.component('category-card', {
        props: {
            category: {
                type: Object,
                required: true
            }
        },
        data: function () {
            return {

            }
        },
        template: `
            <div class="col-md-3">
                <div class="card mb-4 box-shadow" @click="onCardClick">
                    
                    <div class="card-body">

                        <span class="d-inline-block text-truncate" style="max-width: 75%;">
                            <i class="fa fa-circle color-icon" aria-hidden="true"
                                :style="{ color: category.color }"></i>
                            <strong class="card-title">{{ category.name}}</strong>
                        </span>
                        <i class="card-text fa fa-ellipsis-v fa-x icon-more" :id="'dropdownCategory' + category.id"
                            data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" aria-hidden="true"></i>
                        
                        <p v-if="category.numberAnnotations > 0">
                            {{ category.numberAnnotations }} objects have been made with this category.
                        </p>
                        <p v-else>No annotations use this category</p>
                                                
                        <div class="dropdown-menu" :aria-labelledby="'dropdownCategory' + category.id">
                            <a class="dropdown-item" @click="onEditClick">Edit</a>
                            <a class="dropdown-item" @click="onDeleteClick">Delete</a>
                            <a class="dropdown-item" @click="onDownloadClick">Download COCO & Images</a>
                        </div>
                    </div>
                </div>
            </div>
        `,
        computed: {

        },
        methods: {
            onEditClick: function () {

            },
            onCardClick: function () {

            },
            onDownloadClick: function () {
                
            },
            onDeleteClick: function () {
                axios.delete('/api/category/' + this.category.id).then(response => {
                    this.$parent.updatePage()
                })
            }
        },
        created () {
        }
    });
});
