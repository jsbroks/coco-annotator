define(['Vue', 'axios'], function (Vue, axios) {

    Vue.component('image-card', {
        props: {
            image: {
                type: Object,
                required: true
            }
        },
        template: `
            <div class="col-md-3">
                <div class="card mb-4 box-shadow">
                    <img class="card-img-top" @click="openAnnotator" style="width: 100%; display: block;"
                        :src="imageUrl">

                    <div class="card-body">
                    
                        <span class="d-inline-block text-truncate" style="max-width: 85%;">
                            <strong class="card-title">{{ image.id }}. {{ image.file_name}}</strong>
                        </span>
                        
                        <i class="card-text fa fa-ellipsis-v fa-x icon-more" :id="'dropdownImage' + image.id"
                            data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" aria-hidden="true"></i>           
                        
                        <p v-if="image.annotations > 0">
                            {{ image.annotations }} annotations.
                        </p>
                        <p v-else>Image has no annotations</p>
                        
                        <!--<span v-for="category in dataset.categories"-->
                            <!--class="badge badge-pill badge-primary">{{ category.name }}</span>-->
                        
                        <div class="dropdown-menu" :aria-labelledby="'dropdownImage' + image.id">
                            <a class="dropdown-item" @click="onDeleteClick">Delete</a>
                            <a class="dropdown-item" @click="openAnnotator">Annotate</a>
                            <a class="dropdown-item" @click="onDownloadClick">Download Image & COCO</a>
                        </div>
                    </div>
                </div>
            </div>
        `,
        methods: {
            downloadURI: function (uri, exportName) {
                let link = document.createElement("a");
                link.href = uri;
                link.download = exportName;
                document.body.appendChild(link);
                link.click();
                link.remove();
            },
            openAnnotator: function () {
                document.location.pathname = '/annotate/' + this.image.id;
            },
            onDownloadClick: function () {
                this.downloadURI("/api/image/" + this.image.id + "?asAttachment=true", this.image.file_name);

                axios.get("/api/image/" + this.image.id + "/coco").then(reponse => {
                    let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(reponse.data));
                    this.downloadURI(dataStr, this.image.file_name.replace(/\.[^/.]+$/, "") + ".json")
                });
            },
            onDeleteClick: function () {
                axios.delete('/api/image/' + this.image.id).then(response => {
                    this.$parent.updatePage()
                })
            }
        },
        computed: {
            imageUrl: function () {
                return '/api/image/' + this.image.id;
            }
        },
        created () {
            let maxLength = 10;
            if (this.image.file_name.length > maxLength)
                this.name = this.image.file_name.substring(0,maxLength) + '...';
        }
    });
});
