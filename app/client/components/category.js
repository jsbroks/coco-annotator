define(['Vue', 'paper', 'axios', 'annotation'], function (Vue, paper, axios) {

    Vue.component('category', {
        props: {
            category: {
                type: Object,
                required: true
            },
            index: {
                type: Number,
                required: true
            },
            current: {
                type: Object,
                required: true
            },
            hover: {
                type: Object,
                required: true
            },
            opacity: {
                type: Number,
                required: true
            }
        },
        data: function () {
            return {
                group: null,
                color: this.category.color,
                selectedAnnotation: 0,
                collapseAnimation: false
            }
        },
        template: `
            <div class="card"
                :style="{ 'background-color': backgroundColor }">
            
                <div class="card-header" :id="'heading' + category.id">
                    <div :style="{ color: isVisible ? 'white' : 'gray' }">
                        <div @click="onEyeClick">
                            <i v-if="isVisible" class="fa fa-eye category-icon"
                                :style="{ color: isCurrent ? 'white' : color }"
                                aria-hidden="true"></i>
                            <i v-else class="fa fa-eye-slash category-icon" aria-hidden="true"></i>
                        </div>

                        <button class="btn btn-link btn-sm collapsed category-text" style="color: inherit"
                            aria-expanded="false" :aria-controls="'collapse' + category.id"
                            @click="onClick">
                                {{ category.name }} ({{ category.annotations.length }})
                        </button>

                        <i class="fa fa-gear category-icon" data-toggle="modal" :data-target="'#categorySettings' + category.id"
                            style="float: right; color: white" aria-hidden="true"></i>

                        <i @click="createAnnotation" class="fa fa-plus category-icon"
                            style="float: right; color: white; padding-right: 0"
                            aria-hidden="true"></i>
                    </div>
                </div>
                
                <ul :id="'collapse' + category.id" class="collapse list-group"
                    :aria-labelledby="'heading' + category.id">
                    
                    <annotation v-for="(annotation, index) in category.annotations" :key="annotation.id + '-annotation'"
                        :annotation="annotation" :current='current.annotation' @click="onAnnotationClick(index)"
                        :opacity="opacity" :index="index" ref="annotation" :hover="hover.annotation"></annotation>
                </ul>
                
                <div class="modal fade" tabindex="-1" role="dialog" :id="'categorySettings' + category.id">
                    <div class="modal-dialog" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">{{ category.name }}</h5>
                                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                    <span aria-hidden="true">&times;</span>
                                </button>
                            </div>
                            <div class="modal-body">
                                <form>
                                    <div class="form-group row">
                                        <label for="staticEmail" class="col-sm-2 col-form-label">Color</label>
                                        <div class="col-sm-9">
                                            <input v-model="color" type="color" class="form-control">
                                        </div>
                                    </div>
                                </form>  
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                 </div>
            </div>
        `,
        methods: {
            createAnnotation: function() {
                let parent = this.$parent;
                let categories = parent.categories;

                axios.post('/api/annotation/', {
                    image_id: parent.image.id,
                    category_id: this.category.id
                }).then(response => {
                    let category = categories.filter(element => {
                        if (element.id === this.category.id) {
                            return element;
                        }
                    });

                    let annotations = category[0].annotations;

                    annotations.push(response.data);
                    if (this.isCurrent) {
                        parent.current.annotation = annotations.length - 1;
                    }
                });
            },
            export: function () {

                let refs = this.$refs;
                let categoryData = {
                    // Category Identification
                    id: this.category.id,
                    name: this.category.name,

                    // Show in side bar
                    show: this.category.show,
                    // Show groups on canvas
                    visualize: this.category.visualize,
                    color: this.color,

                    metadata: [],

                    annotations: []
                };

                if (refs.hasOwnProperty('annotation')) {
                    refs.annotation.forEach(annotation => {
                        categoryData.annotations.push(annotation.export())
                    });
                }

                return categoryData
            },
            onEyeClick: function () {
                if (this.collapseAnimation) return;
                this.category.visualize = !this.category.visualize;
                if (this.isCurrent) {
                    this.$emit('click', {annotation: this.selectedAnnotation, category: this.index})
                }
            },
            onAnnotationClick: function (index) {
                if (this.collapseAnimation) return;
                let indices = {annotation: index, category: this.index};
                this.selectedAnnotation = index;
                this.$emit('click', indices);
            },
            onClick: function (event) {
                if (this.collapseAnimation) return;
                let indices = {annotation: this.selectedAnnotation, category: this.index};
                this.$emit('click', indices);
            },
            initCategory: function () {
                if (this.group === null) {
                    this.group = new paper.Group();
                    this.group.opacity = this.opacity;
                    this.group.visible = this.isVisible;
                    this.group.data.categoryId = this.index;
                    this.group.clipMask = false;
                }
            },
            getAnnotation: function (index) {
                let ref = this.$refs.annotation;

                if (ref == null) return null;
                if (ref.length < 1 || index >= ref.length) return null;

                return this.$refs.annotation[index];
            },
            collapse: function (state) {
                $("#collapse" + this.category.id).collapse(state);
                this.collapseAnimation = true;
                setTimeout(() => { this.collapseAnimation = false; }, 500);
            },
            setColor: function () {
                if (this.group != null) {
                    this.group.fillColor = this.color;
                    // Strokes cause lag, issue #39
                    //let h = Math.round(this.group.fillColor.hue);
                    //let l = Math.round((this.group.fillColor.lightness - 0.2) * 100);
                    //let s = Math.round(this.group.fillColor.saturation * 100);
                    //this.group.strokeColor = 'hsl(' + h + ',' + s + '%,' + l + '%)'
                }
            }
        },
        watch: {
            color: function () {
                this.setColor()
            },
            opacity: function () {
                if (this.group == null) return;
                this.group.opacity = this.opacity;
            },
            isVisible: function (newVisible, oldVisible) {

                if (this.group == null) return;

                this.group.visible = newVisible;
            },
            isCurrent: function (newValue, oldValue) {
                if (newValue) {
                    this.collapse('show');
                    let annotations = this.$refs.annotation;
                    if (annotations) {
                        annotations.forEach(annotation => {
                            annotation.setColor();
                        });
                    }
                } else {
                    this.collapse('hide');
                    this.setColor()
                }
            },
            group: function (newGroup, oldGroup) {
                if (newGroup != null) {
                    if (this.$refs.annotation != null) {
                        this.$refs.annotation.forEach(child => child.initAnnotation())
                    }
                }
            }
        },
        computed: {
            isVisible: function () {
                return (this.isCurrent || this.category.visualize) && this.category.annotations.length !== 0;
            },
            isCurrent: function () {
                return this.current.category === this.index;
            },
            isHover: function () {
                return this.hover.category === this.index;
            },
            backgroundColor: function () {
                if (this.isHover && !this.isCurrent) {
                    return '#646c82';
                }
                return 'inherit';
            }
        },
        created () {
        },
        mounted () {
            if (this.isCurrent) {
                this.collapse('show');
                let annotations = this.$refs.annotation;
                if (annotations) {
                    annotations.forEach(annotation => {
                        annotation.setColor();
                    });
                }
            }
            this.initCategory()
        }
    });
});
